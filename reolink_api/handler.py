"""
Lambda handler for the Wolf Creek Pass cabin dashboard API.

Serves two endpoints via query parameter routing:
  ?action=sensorpush  — SensorPush sensor readings (direct API, 7-day history)
  (default)           — Reolink camera snapshots for a given date

Designed to be called via Lambda Function URL.
"""

from __future__ import annotations

import json
import logging
import os
import time
import urllib.request
import urllib.error
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from typing import Any

import boto3
from boto3.dynamodb.conditions import Key

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

# ── Camera name mapping ──────────────────────────────────────────────────────
CAMERAS: dict[str, str] = {
    "cabin_entry": "Cabin Entry",
    "cabin_porch": "Cabin Porch",
    "cabin_west": "Cabin West",
    "cabin_driveway": "Cabin Driveway",
    "cabin_shed": "Cabin Shed",
    "cabin_east": "Cabin East",
}

# ── SensorPush sensor mapping ────────────────────────────────────────────────
SENSORS: dict[str, str] = {
    "16851853.10691625321892782031": "Cabin Main",
    "16868601.1531727881802074019": "Cabin Basement",
}

SENSOR_METRICS = [
    "temperature",
    "humidity",
    "dewpoint",
    "barometric_pressure",
    "vpd",
]

# ── Environment ──────────────────────────────────────────────────────────────
REOLINK_TABLE = os.environ.get("REOLINK_TABLE", "reolink-snapshots")
BUCKET_NAME = os.environ.get("REOLINK_BUCKET", "rl-snapshots")
AWS_REGION = os.environ.get("AWS_DEFAULT_REGION", "us-east-1")
SENSORPUSH_EMAIL = os.environ.get("SENSORPUSH_EMAIL", "")
SENSORPUSH_PASSWORD = os.environ.get("SENSORPUSH_PASSWORD", "")

CORS_HEADERS = {
    "Content-Type": "application/json",
    "Access-Control-Allow-Origin": "*",
    "Access-Control-Allow-Methods": "GET, OPTIONS",
    "Access-Control-Allow-Headers": "Content-Type",
}


# ── Shared helpers ───────────────────────────────────────────────────────────


def _decimal_to_float(obj: Any) -> Any:
    """Recursively convert Decimal values to float for JSON serialization."""
    if isinstance(obj, Decimal):
        return float(obj)
    if isinstance(obj, dict):
        return {k: _decimal_to_float(v) for k, v in obj.items()}
    if isinstance(obj, list):
        return [_decimal_to_float(i) for i in obj]
    return obj


def _json_response(status: int, body: Any) -> dict:
    return {
        "statusCode": status,
        "headers": CORS_HEADERS,
        "body": json.dumps(body),
    }


# ═════════════════════════════════════════════════════════════════════════════
# Reolink snapshots
# ═════════════════════════════════════════════════════════════════════════════


def _image_url(s3_key: str) -> str:
    """Construct the public S3 URL for a snapshot image."""
    return f"https://{BUCKET_NAME}.s3.amazonaws.com/{s3_key}"


def _parse_date(raw: str | None) -> str:
    """Validate and return a YYYY-MM-DD date string, defaulting to today UTC."""
    if raw:
        try:
            datetime.strptime(raw, "%Y-%m-%d")
            return raw
        except ValueError:
            pass
    return datetime.now(timezone.utc).strftime("%Y-%m-%d")


def _query_camera(table: Any, camera_id: str, date_str: str) -> list[dict] | None:
    """Query all snapshots for a single camera on a given date.

    Returns None if the table is unreachable (missing, auth error, etc.),
    or a (possibly empty) list of snapshot dicts on success.
    """
    start_ts = f"{date_str}T00:00:00"
    end_ts = f"{date_str}T23:59:59+99:99"

    try:
        response = table.query(
            KeyConditionExpression=(
                Key("camera").eq(camera_id) & Key("timestamp").between(start_ts, end_ts)
            ),
        )
    except Exception as exc:
        logger.warning("DynamoDB query failed for %s: %s", camera_id, exc)
        return None

    snapshots = []
    for item in response.get("Items", []):
        s3_key = item.get("s3_key", "")
        detections = [
            {"label": d["label"], "confidence": _decimal_to_float(d["confidence"])}
            for d in item.get("detections", [])
        ]
        weather = _decimal_to_float(item.get("weather", {}))

        snapshots.append(
            {
                "timestamp": item["timestamp"],
                "image_url": _image_url(s3_key) if s3_key else None,
                "interesting": item.get("interesting", False),
                "detections": detections,
                "weather": weather,
            }
        )

    return sorted(snapshots, key=lambda s: s["timestamp"])


def _handle_reolink(params: dict) -> dict:
    """Handle ?action=reolink (or default) — camera snapshots by date."""
    date_str = _parse_date(params.get("date"))

    dynamodb = boto3.resource("dynamodb", region_name=AWS_REGION)
    table = dynamodb.Table(REOLINK_TABLE)

    # Probe the table with the first camera; if it fails, skip all cameras.
    camera_ids = list(CAMERAS.items())
    cameras = []
    first_id, first_name = camera_ids[0]
    first_snapshots = _query_camera(table, first_id, date_str)
    if first_snapshots is None:
        # Table unreachable — return empty results for all cameras
        for camera_id, display_name in camera_ids:
            cameras.append({"id": camera_id, "name": display_name, "snapshots": []})
        return _json_response(200, {"date": date_str, "cameras": cameras})

    cameras.append({"id": first_id, "name": first_name, "snapshots": first_snapshots})
    for camera_id, display_name in camera_ids[1:]:
        snapshots = _query_camera(table, camera_id, date_str)
        cameras.append(
            {
                "id": camera_id,
                "name": display_name,
                "snapshots": snapshots or [],
            }
        )

    return _json_response(200, {"date": date_str, "cameras": cameras})


# ═════════════════════════════════════════════════════════════════════════════
# SensorPush — direct API access (no DynamoDB)
# ═════════════════════════════════════════════════════════════════════════════

_SP_BASE = "https://api.sensorpush.com/api/v1"
_SP_HEADERS = {
    "Accept": "application/json",
    "Content-Type": "application/json",
}

# Module-level caches (persist across Lambda container invocations)
_sp_access_token: str | None = None
_sp_token_expiry: float = 0

# Response cache — keyed by mode ("summary" or "history")
_sp_response_cache: dict[str, dict] = {}
_sp_cache_ts: dict[str, float] = {}
_SP_CACHE_TTL = 300  # 5 minutes


def _sp_post(url: str, body: dict, headers: dict, timeout: int = 30) -> dict | None:
    """POST JSON to a URL, return parsed JSON or None on failure."""
    data = json.dumps(body).encode()
    req = urllib.request.Request(url, data=data, headers=headers, method="POST")
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return json.loads(resp.read().decode())
    except (urllib.error.URLError, json.JSONDecodeError, OSError) as exc:
        logger.warning("SensorPush POST %s failed: %s", url, exc)
        return None


def _sp_authorize() -> str | None:
    """Exchange credentials for an authorization code."""
    data = _sp_post(
        f"{_SP_BASE}/oauth/authorize",
        {"email": SENSORPUSH_EMAIL, "password": SENSORPUSH_PASSWORD},
        _SP_HEADERS,
    )
    if data:
        return data.get("authorization")
    return None


def _sp_get_token(auth_code: str) -> str | None:
    """Exchange auth code for an access token."""
    data = _sp_post(
        f"{_SP_BASE}/oauth/accesstoken",
        {"authorization": auth_code},
        _SP_HEADERS,
    )
    if data:
        return data.get("accesstoken")
    return None


def _sp_ensure_token() -> str | None:
    """Ensure we have a valid SensorPush access token, refreshing if needed."""
    global _sp_access_token, _sp_token_expiry

    if _sp_access_token and time.time() < _sp_token_expiry:
        return _sp_access_token

    logger.info("SensorPush: refreshing access token")
    auth_code = _sp_authorize()
    if not auth_code:
        logger.warning("SensorPush: failed to get authorization code")
        return None

    token = _sp_get_token(auth_code)
    if not token:
        logger.warning("SensorPush: failed to get access token")
        return None

    _sp_access_token = token
    # Token valid for 12 hours; refresh 5 minutes early
    _sp_token_expiry = time.time() + (12 * 3600) - 300
    return token


def _sp_request(endpoint: str, body: dict) -> dict | None:
    """Make an authenticated SensorPush API request with auto-retry on 401."""
    token = _sp_ensure_token()
    if not token:
        return None

    headers = {**_SP_HEADERS, "Authorization": token}
    url = f"{_SP_BASE}{endpoint}"

    data = json.dumps(body).encode()
    req = urllib.request.Request(url, data=data, headers=headers, method="POST")
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            return json.loads(resp.read().decode())
    except urllib.error.HTTPError as exc:
        if exc.code == 401:
            logger.info("SensorPush 401 on %s — re-authenticating", endpoint)
            global _sp_access_token, _sp_token_expiry
            _sp_access_token = None
            _sp_token_expiry = 0
            token = _sp_ensure_token()
            if not token:
                return None
            headers = {**_SP_HEADERS, "Authorization": token}
            req = urllib.request.Request(url, data=data, headers=headers, method="POST")
            try:
                with urllib.request.urlopen(req, timeout=30) as resp2:
                    return json.loads(resp2.read().decode())
            except Exception as exc2:
                logger.warning("SensorPush retry failed: %s", exc2)
                return None
        logger.warning("SensorPush API %s failed: %s", endpoint, exc)
        return None
    except (urllib.error.URLError, json.JSONDecodeError, OSError) as exc:
        logger.warning("SensorPush API %s failed: %s", endpoint, exc)
        return None


def _sp_fetch_samples(
    sensor_ids: list[str], days: int, limit_per_page: int = 2500
) -> dict[str, list[dict]]:
    """Fetch samples for the given sensors over the last N days.

    Uses ``last_time`` from each response as the pagination cursor
    (advancing startTime forward through time).  The API returns up to
    ``limit`` samples per sensor per page, newest-first within each page.

    Returns:
        Dict mapping sensor_id → list of sample dicts (oldest first).
    """
    start_ts = (datetime.now(timezone.utc) - timedelta(days=days)).isoformat()
    all_samples: dict[str, list[dict]] = {sid: [] for sid in sensor_ids}
    max_pages = 15  # safety limit

    for page_num in range(max_pages):
        body: dict[str, Any] = {
            "sensors": sensor_ids,
            "startTime": start_ts,
            "limit": limit_per_page,
            "measures": SENSOR_METRICS,
        }

        t0 = time.time()
        data = _sp_request("/samples", body)
        elapsed = time.time() - t0
        if not data:
            break

        sensors_data = data.get("sensors", {})
        page_total = 0
        any_full = False
        for sid in sensor_ids:
            samples = sensors_data.get(sid, [])
            page_total += len(samples)
            all_samples[sid].extend(samples)
            if len(samples) >= limit_per_page:
                any_full = True

        last_time = data.get("last_time", "")
        logger.info(
            "SensorPush page %d: %d samples, last_time=%s, %.1fs",
            page_num + 1,
            page_total,
            last_time[:19] if last_time else "?",
            elapsed,
        )

        # Stop if no sensor returned a full page (we have all data)
        if not any_full or not last_time:
            break

        # Advance startTime to last_time for next page
        start_ts = last_time

    # Sort each sensor's samples by observed timestamp (oldest first)
    for sid in all_samples:
        all_samples[sid].sort(key=lambda s: s.get("observed", ""))

    return all_samples


def _compute_ranges(
    samples: list[dict], cutoff_12h: str, cutoff_24h: str
) -> tuple[dict | None, dict, dict, dict]:
    """Compute current reading, 12h/24h ranges, and 24h averages.

    Returns (current, range_12h, range_24h, avg_24h).  Range dicts map
    metric_name → {"min": float, "max": float}.  avg_24h maps
    metric_name → float.  ``current`` is the latest reading dict or None.
    """
    if not samples:
        return None, {}, {}, {}

    current_item = samples[-1]
    current: dict[str, Any] = {"timestamp": current_item.get("observed", "")}
    for metric in SENSOR_METRICS:
        val = current_item.get(metric)
        if val is not None:
            current[metric] = float(val)

    range_12h: dict[str, dict[str, float]] = {}
    range_24h: dict[str, dict[str, float]] = {}
    sum_24h: dict[str, float] = {}
    count_24h: dict[str, int] = {}

    for item in samples:
        ts = item.get("observed", "")
        for metric in SENSOR_METRICS:
            raw = item.get(metric)
            if raw is None:
                continue
            val = float(raw)

            # 24h range + average accumulators
            if ts >= cutoff_24h:
                if metric not in range_24h:
                    range_24h[metric] = {"min": val, "max": val}
                    sum_24h[metric] = val
                    count_24h[metric] = 1
                else:
                    range_24h[metric]["min"] = min(range_24h[metric]["min"], val)
                    range_24h[metric]["max"] = max(range_24h[metric]["max"], val)
                    sum_24h[metric] += val
                    count_24h[metric] += 1

            # 12h range
            if ts >= cutoff_12h:
                if metric not in range_12h:
                    range_12h[metric] = {"min": val, "max": val}
                else:
                    range_12h[metric]["min"] = min(range_12h[metric]["min"], val)
                    range_12h[metric]["max"] = max(range_12h[metric]["max"], val)

    avg_24h: dict[str, float] = {}
    for metric in sum_24h:
        avg_24h[metric] = round(sum_24h[metric] / count_24h[metric], 2)

    return current, range_12h, range_24h, avg_24h


def _downsample_series(samples: list[dict], max_points: int = 168) -> list[dict]:
    """Downsample a time series to at most max_points for chart rendering.

    Default 168 = one point per hour over 7 days — sufficient for a sparkline.
    Selects evenly-spaced points.  Always includes first and last.
    """
    n = len(samples)
    if n <= max_points:
        return samples

    step = (n - 1) / (max_points - 1)
    indices = {0, n - 1}
    for i in range(1, max_points - 1):
        indices.add(round(i * step))

    return [samples[i] for i in sorted(indices)]


def _build_time_series(samples: list[dict]) -> dict[str, list]:
    """Build per-metric time series arrays for charting.

    Returns dict mapping metric → list of [timestamp_iso, value] pairs.
    """
    series: dict[str, list] = {}
    for metric in SENSOR_METRICS:
        points = []
        for s in samples:
            val = s.get(metric)
            if val is not None:
                points.append([s.get("observed", ""), round(float(val), 2)])
        if points:
            series[metric] = points
    return series


def _build_sensor_response(include_history: bool) -> dict:
    """Build the sensor response body.

    Args:
        include_history: If True, fetch 7 days of data and include time_series
            and range data.  If False, fetch only the most recent reading per
            sensor (fast summary).
    """
    sensor_ids = list(SENSORS.keys())

    if not include_history:
        # ── Summary mode — just the latest reading per sensor ────────────
        data = _sp_request("/samples", {"sensors": sensor_ids, "limit": 1})
        sensors = []
        for sensor_id, display_name in SENSORS.items():
            raw_samples = data.get("sensors", {}).get(sensor_id, []) if data else []
            logger.info("SensorPush summary %s: %s", display_name, raw_samples)

            current = None
            if raw_samples:
                s = raw_samples[-1]
                current = {"timestamp": s.get("observed", "")}
                for metric in SENSOR_METRICS:
                    val = s.get(metric)
                    if val is not None:
                        current[metric] = float(val)

            sensors.append(
                {
                    "id": sensor_id,
                    "name": display_name,
                    "current": current,
                    "range_12h": {},
                    "range_24h": {},
                    "avg_24h": {},
                    "reading_count": 0,
                    "time_series": {},
                }
            )
        return {"sensors": sensors}

    # ── History mode — full 7-day fetch with ranges + charts ─────────────
    all_samples = _sp_fetch_samples(sensor_ids, days=7)

    cutoff_24h = (datetime.now(timezone.utc) - timedelta(hours=24)).isoformat()
    cutoff_12h = (datetime.now(timezone.utc) - timedelta(hours=12)).isoformat()

    sensors = []
    for sensor_id, display_name in SENSORS.items():
        samples = all_samples.get(sensor_id, [])

        current, range_12h, range_24h, avg_24h = _compute_ranges(
            samples, cutoff_12h, cutoff_24h
        )

        time_series: dict[str, list] = {}
        if samples:
            chart_samples = _downsample_series(samples)
            time_series = _build_time_series(chart_samples)

        sensors.append(
            {
                "id": sensor_id,
                "name": display_name,
                "current": current,
                "range_12h": range_12h,
                "range_24h": range_24h,
                "avg_24h": avg_24h,
                "reading_count": len(samples),
                "time_series": time_series,
            }
        )

    return {"sensors": sensors}


def _handle_sensorpush(params: dict) -> dict:
    """Handle ?action=sensorpush — live sensor data from SensorPush API.

    Query params:
        history=1  — include 7-day time series data (slow first load, cached)
        (default)  — summary only with current readings (fast)
    """
    if not SENSORPUSH_EMAIL or not SENSORPUSH_PASSWORD:
        return _json_response(500, {"error": "SensorPush credentials not configured"})

    include_history = params.get("history") == "1"
    cache_key = "history" if include_history else "summary"

    # Check response cache
    cached_ts = _sp_cache_ts.get(cache_key, 0)
    if cache_key in _sp_response_cache and (time.time() - cached_ts) < _SP_CACHE_TTL:
        logger.info(
            "SensorPush %s: serving from cache (age %.0fs)",
            cache_key,
            time.time() - cached_ts,
        )
        return _sp_response_cache[cache_key]

    logger.info("SensorPush %s: fetching fresh data", cache_key)
    body = _build_sensor_response(include_history)
    response = _json_response(200, body)

    # Cache the response
    _sp_response_cache[cache_key] = response
    _sp_cache_ts[cache_key] = time.time()

    return response


# ═════════════════════════════════════════════════════════════════════════════
# Lambda entry point
# ═════════════════════════════════════════════════════════════════════════════


def handler(event: dict, context: Any) -> dict:
    """Route requests based on the 'action' query parameter."""
    # OPTIONS preflight
    http_method = event.get("requestContext", {}).get("http", {}).get("method", "GET")
    if http_method == "OPTIONS":
        return {"statusCode": 204, "headers": CORS_HEADERS, "body": ""}

    params = event.get("queryStringParameters") or {}
    action = params.get("action", "reolink")

    if action == "sensorpush":
        return _handle_sensorpush(params)

    return _handle_reolink(params)
