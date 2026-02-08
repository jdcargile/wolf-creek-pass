"""
Export capture cycle data as JSON for the Vue frontend.

Generates per-cycle JSON files and an index of all cycles.
Files are saved locally or uploaded to S3 depending on storage backend.
"""

from __future__ import annotations

import json
from pathlib import Path

from rich.console import Console

from models import (
    CaptureRecord,
    CycleSummary,
    Event,
    RoadCondition,
    Route,
    WeatherStation,
)
from storage import Storage

console = Console()

OUTPUT_DIR = Path("output/data")


def export_cycle_json(
    storage: Storage,
    cycle: CycleSummary,
    route: Route | None = None,
) -> dict:
    """Build the full JSON payload for a capture cycle."""
    captures = storage.get_captures_by_cycle(cycle.cycle_id)
    conditions = storage.get_road_conditions(cycle.cycle_id)
    events = storage.get_events(cycle.cycle_id)
    weather = storage.get_weather(cycle.cycle_id)

    data = {
        "cycle": cycle.model_dump(),
        "route": route.model_dump() if route else None,
        "captures": [_capture_to_dict(c, storage) for c in captures],
        "conditions": [c.model_dump() for c in conditions],
        "events": [e.model_dump() for e in events],
        "weather": [w.model_dump() for w in weather],
    }

    return data


def export_cycle_to_file(
    storage: Storage,
    cycle: CycleSummary,
    route: Route | None = None,
) -> Path:
    """Export a cycle's data to a local JSON file."""
    data = export_cycle_json(storage, cycle, route)

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    # Per-cycle file
    safe_id = cycle.cycle_id.replace(":", "-")
    cycle_path = OUTPUT_DIR / f"cycle-{safe_id}.json"
    cycle_path.write_text(json.dumps(data, indent=2, default=str))

    # Latest symlink / copy
    latest_path = OUTPUT_DIR / "latest.json"
    latest_path.write_text(json.dumps(data, indent=2, default=str))

    console.print(f"Exported cycle data to [dim]{cycle_path}[/dim]")
    return cycle_path


def export_cycle_index(storage: Storage) -> Path:
    """Export an index of all capture cycles."""
    cycles = storage.get_cycles(limit=200)

    index = {
        "cycles": [c.model_dump() for c in cycles],
        "count": len(cycles),
    }

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    index_path = OUTPUT_DIR / "index.json"
    index_path.write_text(json.dumps(index, indent=2, default=str))

    console.print(
        f"Exported cycle index ({len(cycles)} cycles) to [dim]{index_path}[/dim]"
    )
    return index_path


def _capture_to_dict(capture: CaptureRecord, storage: Storage) -> dict:
    """Convert a capture to a dict with a resolved image URL."""
    d = capture.model_dump()
    if capture.image_key:
        d["image_url"] = storage.get_image_url(capture.image_key)
    return d
