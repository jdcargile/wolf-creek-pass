"""
Export capture cycle data as JSON for the Vue frontend.

Generates per-cycle JSON files and an index of all cycles.
Outputs to local filesystem (dev) or S3 (deployed), controlled by settings.
"""

from __future__ import annotations

import json
from pathlib import Path

import boto3
from rich.console import Console

from models import CaptureRecord, CycleSummary, Route
from settings import Settings
from storage import Storage

console = Console()

OUTPUT_DIR = Path("output/data")


def _get_s3_client(settings: Settings):
    """Create an S3 client if using dynamo backend."""
    kwargs = {}
    if settings.aws_endpoint_url:
        kwargs["endpoint_url"] = settings.aws_endpoint_url
    return boto3.client("s3", region_name=settings.aws_default_region, **kwargs)


def _write_json(key: str, data: dict, settings: Settings) -> str:
    """Write JSON to local filesystem or S3 depending on backend."""
    payload = json.dumps(data, indent=2, default=str)

    if settings.storage_backend == "dynamo":
        s3 = _get_s3_client(settings)
        s3_key = f"data/{key}"
        s3.put_object(
            Bucket=settings.bucket_name,
            Key=s3_key,
            Body=payload.encode(),
            ContentType="application/json",
        )
        console.print(f"Exported [dim]s3://{settings.bucket_name}/{s3_key}[/dim]")
        return f"s3://{settings.bucket_name}/{s3_key}"
    else:
        OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
        path = OUTPUT_DIR / key
        path.write_text(payload)
        console.print(f"Exported [dim]{path}[/dim]")
        return str(path)


def export_cycle_json(
    storage: Storage,
    cycle: CycleSummary,
    routes: list[Route] | None = None,
) -> dict:
    """Build the full JSON payload for a capture cycle."""
    captures = storage.get_captures_by_cycle(cycle.cycle_id)
    conditions = storage.get_road_conditions(cycle.cycle_id)
    events = storage.get_events(cycle.cycle_id)
    weather = storage.get_weather(cycle.cycle_id)
    passes = storage.get_mountain_passes(cycle.cycle_id)
    plows = storage.get_snow_plows(cycle.cycle_id)

    return {
        "cycle": cycle.model_dump(),
        "routes": [r.model_dump() for r in routes] if routes else [],
        "captures": [_capture_to_dict(c, storage) for c in captures],
        "conditions": [c.model_dump() for c in conditions],
        "events": [e.model_dump() for e in events],
        "weather": [w.model_dump() for w in weather],
        "passes": [p.model_dump() for p in passes],
        "plows": [p.model_dump() for p in plows],
    }


def export_cycle_to_file(
    storage: Storage,
    cycle: CycleSummary,
    routes: list[Route] | None = None,
    settings: Settings | None = None,
) -> str:
    """Export a cycle's data to a JSON file (local or S3)."""
    if settings is None:
        settings = Settings()

    data = export_cycle_json(storage, cycle, routes)

    # Per-cycle file
    safe_id = cycle.cycle_id.replace(":", "-")
    _write_json(f"cycle-{safe_id}.json", data, settings)

    # Latest
    _write_json("latest.json", data, settings)

    return f"cycle-{safe_id}.json"


def export_cycle_index(
    storage: Storage,
    settings: Settings | None = None,
) -> str:
    """Export an index of all capture cycles."""
    if settings is None:
        settings = Settings()

    cycles = storage.get_cycles(limit=200)
    index = {
        "cycles": [c.model_dump() for c in cycles],
        "count": len(cycles),
    }

    _write_json("index.json", index, settings)
    console.print(f"Exported cycle index ({len(cycles)} cycles)")
    return "index.json"


def _capture_to_dict(capture: CaptureRecord, storage: Storage) -> dict:
    """Convert a capture to a dict with a resolved image URL."""
    d = capture.model_dump()
    if capture.image_key:
        d["image_url"] = storage.get_image_url(capture.image_key)
    return d
