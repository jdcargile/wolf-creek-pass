"""
Lambda handler for querying Reolink camera snapshots from DynamoDB.

Returns all camera snapshots for a given date, with S3 image URLs and
detection/weather metadata.  Designed to be called via Lambda Function URL.
"""

from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from decimal import Decimal
from typing import Any

import boto3
from boto3.dynamodb.conditions import Key

# ── Camera name mapping ──────────────────────────────────────────────────────
CAMERAS: dict[str, str] = {
    "cabin_entry": "Cabin Entry",
    "cabin_porch": "Cabin Porch",
    "cabin_west": "Cabin West",
    "cabin_driveway": "Cabin Driveway",
    "cabin_shed": "Cabin Shed",
    "cabin_east": "Cabin East",
}

# ── Environment ──────────────────────────────────────────────────────────────
TABLE_NAME = os.environ.get("REOLINK_TABLE", "reolink-snapshots")
BUCKET_NAME = os.environ.get("REOLINK_BUCKET", "rl-snapshots")
AWS_REGION = os.environ.get("AWS_DEFAULT_REGION", "us-east-1")

CORS_HEADERS = {
    "Content-Type": "application/json",
    "Access-Control-Allow-Origin": "*",
    "Access-Control-Allow-Methods": "GET, OPTIONS",
    "Access-Control-Allow-Headers": "Content-Type",
}


# ── Helpers ──────────────────────────────────────────────────────────────────


def _decimal_to_float(obj: Any) -> Any:
    """Recursively convert Decimal values to float for JSON serialization."""
    if isinstance(obj, Decimal):
        return float(obj)
    if isinstance(obj, dict):
        return {k: _decimal_to_float(v) for k, v in obj.items()}
    if isinstance(obj, list):
        return [_decimal_to_float(i) for i in obj]
    return obj


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


# ── Lambda entry point ───────────────────────────────────────────────────────


def handler(event: dict, context: Any) -> dict:
    """Handle Lambda Function URL invocations."""
    # OPTIONS preflight
    http_method = event.get("requestContext", {}).get("http", {}).get("method", "GET")
    if http_method == "OPTIONS":
        return {"statusCode": 204, "headers": CORS_HEADERS, "body": ""}

    # Parse query parameters
    params = event.get("queryStringParameters") or {}
    date_str = _parse_date(params.get("date"))

    # Query DynamoDB
    dynamodb = boto3.resource("dynamodb", region_name=AWS_REGION)
    table = dynamodb.Table(TABLE_NAME)

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

    body = json.dumps({"date": date_str, "cameras": cameras})

    return {"statusCode": 200, "headers": CORS_HEADERS, "body": body}
