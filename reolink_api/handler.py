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


def _query_camera(table: Any, camera_id: str, date_str: str) -> list[dict]:
    """Query all snapshots for a single camera on a given date."""
    start_ts = f"{date_str}T00:00:00"
    end_ts = f"{date_str}T23:59:59+99:99"

    response = table.query(
        KeyConditionExpression=(
            Key("camera").eq(camera_id) & Key("timestamp").between(start_ts, end_ts)
        ),
    )

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

    cameras = []
    for camera_id, display_name in CAMERAS.items():
        snapshots = _query_camera(table, camera_id, date_str)
        cameras.append(
            {
                "id": camera_id,
                "name": display_name,
                "snapshots": snapshots,
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

# Module-level token cache (persists across Lambda container invocations)
_sp_access_token: str | None = None
_sp_token_expiry: float = 0


def _sp_post(url: str, body: dict, headers: dict, timeout: int = 15) -> dict | None:
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
        with urllib.request.urlopen(req, timeout=15) as resp:
            return json.loads(resp.read().decode())
    except urllib.error.HTTPError as exc:
        if exc.code == 401:
            # Token revoked — retry once with fresh token
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
                with urllib.request.urlopen(req, timeout=15) as resp2:
                    return json.loads(resp2.read().decode())
            except Exception as exc2:
                logger.warning("SensorPush retry failed: %s", exc2)
                return None
        logger.warning("SensorPush API %s failed: %s", endpoint, exc)
        return None
    except (urllib.error.URLError, json.JSONDecodeError, OSError) as exc:
        logger.warning("SensorPush API %s failed: %s", endpoint, exc)
        return None


def _sp_fetch_samples(sensor_ids: list[str], minutes: int) -> dict[str, list[dict]]:
    """Fetch samples for the given sensors over the last N minutes.

    The SensorPush /samples endpoint returns at most ~2500 samples per call.
    With 2 sensors at 5-min intervals, 7 days ≈ 4032 samples, so we may
    need to paginate.  Results are returned newest-first from the API.

    Returns:
        Dict mapping sensor_id → list of sample dicts (oldest first).
    """
    start_ts = (datetime.now(timezone.utc) - timedelta(minutes=minutes)).isoformat()
    all_samples: dict[str, list[dict]] = {sid: [] for sid in sensor_ids}
    last_ts: str | None = None
    max_pages = 10  # safety limit

    for _ in range(max_pages):
        body: dict[str, Any] = {
            "sensors": sensor_ids,
            "startTime": start_ts,
            "limit": 2500,
        }
        if last_ts:
            body["stopTime"] = last_ts

        data = _sp_request("/samples", body)
        if not data:
            break

        sensors_data = data.get("sensors", {})
        page_count = 0
        for sid in sensor_ids:
            samples = sensors_data.get(sid, [])
            page_count += len(samples)
            all_samples[sid].extend(samples)

        # If we got fewer than the limit, we have all the data
        total_returned = data.get("total_samples", page_count)
        if page_count < 2500 or total_returned < 2500:
            break

        # Find the oldest timestamp in this page for pagination
        oldest_in_page: str | None = None
        for sid in sensor_ids:
            samples = sensors_data.get(sid, [])
            if samples:
                ts = samples[-1].get("observed", "")
                if oldest_in_page is None or ts < oldest_in_page:
                    oldest_in_page = ts
        if oldest_in_page:
            last_ts = oldest_in_page
        else:
            break

    # Sort each sensor's samples by observed timestamp (oldest first)
    for sid in all_samples:
        all_samples[sid].sort(key=lambda s: s.get("observed", ""))

    return all_samples


def _compute_ranges(
    samples: list[dict], cutoff_12h: str, cutoff_24h: str
) -> tuple[dict | None, dict, dict]:
    """Compute current reading, 12h ranges, and 24h ranges from samples.

    Returns (current, range_12h, range_24h).  Each range dict maps
    metric_name → {"min": float, "max": float}.  ``current`` is the latest
    reading dict or None when the list is empty.
    """
    if not samples:
        return None, {}, {}

    current_item = samples[-1]
    current: dict[str, Any] = {"timestamp": current_item.get("observed", "")}
    for metric in SENSOR_METRICS:
        val = current_item.get(metric)
        if val is not None:
            current[metric] = float(val)

    range_12h: dict[str, dict[str, float]] = {}
    range_24h: dict[str, dict[str, float]] = {}

    for item in samples:
        ts = item.get("observed", "")
        for metric in SENSOR_METRICS:
            raw = item.get(metric)
            if raw is None:
                continue
            val = float(raw)

            # 24h range
            if ts >= cutoff_24h:
                if metric not in range_24h:
                    range_24h[metric] = {"min": val, "max": val}
                else:
                    range_24h[metric]["min"] = min(range_24h[metric]["min"], val)
                    range_24h[metric]["max"] = max(range_24h[metric]["max"], val)

            # 12h range
            if ts >= cutoff_12h:
                if metric not in range_12h:
                    range_12h[metric] = {"min": val, "max": val}
                else:
                    range_12h[metric]["min"] = min(range_12h[metric]["min"], val)
                    range_12h[metric]["max"] = max(range_12h[metric]["max"], val)

    return current, range_12h, range_24h


def _downsample_series(samples: list[dict], max_points: int = 500) -> list[dict]:
    """Downsample a time series to at most max_points for chart rendering.

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

    Returns:
        Dict mapping metric → list of [timestamp_iso, value] pairs.
        Also includes a "timestamps" key with the raw ISO timestamps.
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


def _handle_sensorpush(_params: dict) -> dict:
    """Handle ?action=sensorpush — live sensor data from SensorPush API."""
    if not SENSORPUSH_EMAIL or not SENSORPUSH_PASSWORD:
        return _json_response(500, {"error": "SensorPush credentials not configured"})

    sensor_ids = list(SENSORS.keys())

    # Fetch 7 days of samples
    seven_days_min = 7 * 24 * 60
    all_samples = _sp_fetch_samples(sensor_ids, seven_days_min)

    now_iso = datetime.now(timezone.utc).isoformat()
    cutoff_24h = (datetime.now(timezone.utc) - timedelta(hours=24)).isoformat()
    cutoff_12h = (datetime.now(timezone.utc) - timedelta(hours=12)).isoformat()

    sensors = []
    for sensor_id, display_name in SENSORS.items():
        samples = all_samples.get(sensor_id, [])

        # Compute summary ranges from the full 7-day dataset
        # (24h/12h filters are applied inside _compute_ranges)
        current, range_12h, range_24h = _compute_ranges(samples, cutoff_12h, cutoff_24h)

        # Build time series for graphs (downsampled for frontend perf)
        chart_samples = _downsample_series(samples)
        time_series = _build_time_series(chart_samples)

        sensors.append(
            {
                "id": sensor_id,
                "name": display_name,
                "current": current,
                "range_12h": range_12h,
                "range_24h": range_24h,
                "reading_count": len(samples),
                "time_series": time_series,
            }
        )

    return _json_response(200, {"sensors": sensors})


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
