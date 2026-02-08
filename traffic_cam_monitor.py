#!/usr/bin/env python3
"""
Wolf Creek Pass -- Route-Aware Traffic Camera Monitor

Orchestrates the full capture cycle:
1. Check Wolf Creek Pass closure status (UDOT API)
2. Get routes (UDOT 511 shared route API)
3. Fetch cameras along routes (conditional on closure status)
4. Download camera images and store them
5. Fetch road conditions, events, weather, passes, plows (UDOT API)
6. Store everything (DynamoDB or SQLite)
7. Export JSON for Vue frontend
"""

import hashlib
import time
from datetime import datetime

import click
import requests
import schedule
from rich.console import Console
from rich.panel import Panel

from export import export_cycle_index, export_cycle_to_file
from models import CaptureRecord, CycleSummary
from route import get_routes
from settings import (
    Settings,
    get_all_camera_ids,
    get_all_pass_ids,
    get_all_weather_station_names,
)
from storage import create_storage
from udot import (
    fetch_all_cameras,
    fetch_route_conditions,
    fetch_route_events,
    fetch_route_passes,
    fetch_route_plows,
    fetch_route_weather,
    is_wolf_creek_closed,
)

console = Console()


def run_capture_cycle(settings: Settings) -> None:
    """Run one complete capture cycle."""
    storage = create_storage(settings)
    storage.init()

    cycle_id = datetime.now().strftime("%Y-%m-%dT%H:%M:%S")
    cycle = CycleSummary(cycle_id=cycle_id, started_at=cycle_id)

    console.rule(f"[bold blue]Capture cycle {cycle_id}[/bold blue]")

    # 1. Check Wolf Creek Pass closure status (informational)
    try:
        is_wolf_creek_closed(settings.udot_api_key)
    except Exception as e:
        console.print(f"[yellow]Wolf Creek status check failed:[/yellow] {e}")

    # 2. Get route(s) from UDOT 511 shared route API
    routes = []
    try:
        routes = get_routes()
        storage.save_routes(routes)
    except Exception as e:
        console.print(f"[yellow]Route fetch failed (continuing without):[/yellow] {e}")
        routes = storage.get_routes()

    primary_route = routes[0] if routes else None

    # 3. Fetch cameras for all configured routes
    camera_ids = get_all_camera_ids()
    all_cameras = fetch_all_cameras(settings.udot_api_key)
    camera_lookup = {c.Id: c for c in all_cameras}
    cameras = [camera_lookup[cid] for cid in camera_ids if cid in camera_lookup]
    console.print(
        f"Matched [bold]{len(cameras)}[/bold] of {len(camera_ids)} "
        f"hardcoded route cameras"
    )

    # 4. Download camera images
    skipped_count = 0

    for camera in cameras:
        console.print(
            f"\n[bold]Camera {camera.Id}[/bold] -- "
            f"{camera.Location} ({camera.Roadway} {camera.Direction})"
        )

        # Save camera metadata
        storage.save_camera(camera)

        # Download image
        image_data = _download_image(camera)
        if not image_data:
            continue

        # Check image hash -- skip save if unchanged from last cycle
        image_hash = hashlib.sha256(image_data).hexdigest()
        prev_hash = storage.get_image_hash(camera.Id)

        if prev_hash == image_hash:
            # Image unchanged -- reuse previous image key
            console.print("  [dim]Image unchanged -- skipping[/dim]")
            skipped_count += 1
            prev_captures = storage.get_recent_captures(limit=100)
            prev = next((c for c in prev_captures if c.camera_id == camera.Id), None)
            capture = CaptureRecord(
                camera_id=camera.Id,
                cycle_id=cycle_id,
                image_key=prev.image_key if prev else "",
                roadway=camera.Roadway,
                direction=camera.Direction,
                location=camera.Location,
                latitude=camera.Latitude,
                longitude=camera.Longitude,
            )
            storage.save_capture(capture)
            continue

        # New image -- save
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        image_key = f"cam_{camera.Id}_{timestamp}.jpg"
        storage.save_image(image_key, image_data)
        storage.save_image_hash(camera.Id, image_hash)

        # Build capture record (denormalized)
        capture = CaptureRecord(
            camera_id=camera.Id,
            cycle_id=cycle_id,
            image_key=image_key,
            roadway=camera.Roadway,
            direction=camera.Direction,
            location=camera.Location,
            latitude=camera.Latitude,
            longitude=camera.Longitude,
        )
        storage.save_capture(capture)
        console.print("  [green]Saved[/green]")

    # 5. Fetch UDOT enrichment data (non-fatal -- don't let this block export)
    conditions, events, weather = [], [], []
    if primary_route and primary_route.polyline:
        try:
            conditions = fetch_route_conditions(settings.udot_api_key, primary_route)
            storage.save_road_conditions(cycle_id, conditions)
            console.print(f"Saved [bold]{len(conditions)}[/bold] road conditions")
        except Exception as e:
            console.print(f"[yellow]Road conditions failed (continuing):[/yellow] {e}")

        try:
            events = fetch_route_events(settings.udot_api_key, primary_route)
            storage.save_events(cycle_id, events)
            console.print(f"Saved [bold]{len(events)}[/bold] events")
        except Exception as e:
            console.print(f"[yellow]Events failed (continuing):[/yellow] {e}")

    try:
        weather = fetch_route_weather(
            settings.udot_api_key, get_all_weather_station_names()
        )
        storage.save_weather(cycle_id, weather)
        console.print(f"Saved [bold]{len(weather)}[/bold] weather stations")
    except Exception as e:
        console.print(f"[yellow]Weather failed (continuing):[/yellow] {e}")

    # 5b. Fetch mountain pass conditions (by configured IDs)
    try:
        passes = fetch_route_passes(settings.udot_api_key, get_all_pass_ids())
        storage.save_mountain_passes(cycle_id, passes)
        console.print(f"Saved [bold]{len(passes)}[/bold] mountain pass conditions")
    except Exception as e:
        console.print(f"[yellow]Mountain passes failed (continuing):[/yellow] {e}")

    # 5c. Fetch snow plows near all routes
    try:
        plows = fetch_route_plows(settings.udot_api_key, routes)
        storage.save_snow_plows(cycle_id, plows)
        console.print(f"Saved [bold]{len(plows)}[/bold] snow plows")
    except Exception as e:
        console.print(f"[yellow]Snow plows failed (continuing):[/yellow] {e}")

    # 6. Save cycle summary (use primary route for travel time/distance)
    cycle.completed_at = datetime.now().isoformat()
    cycle.cameras_processed = len(cameras)
    cycle.event_count = len(events)
    cycle.travel_time_s = primary_route.duration_s if primary_route else None
    cycle.distance_m = primary_route.distance_m if primary_route else None
    storage.save_cycle(cycle)

    # 7. Export JSON for Vue
    export_cycle_to_file(storage, cycle, routes, settings)
    export_cycle_index(storage, settings)

    analyzed = len(cameras) - skipped_count
    console.rule(
        f"[bold blue]Cycle complete -- {len(cameras)} cameras, "
        f"{analyzed} new, {skipped_count} cached[/bold blue]"
    )


def _download_image(camera) -> bytes | None:
    """Download current image from a camera. Returns raw bytes or None."""
    if not camera.Views:
        console.print(f"  [yellow]No views for camera {camera.Id}[/yellow]")
        return None

    url = camera.Views[0].Url
    if not url:
        console.print(f"  [yellow]No URL for camera {camera.Id}[/yellow]")
        return None

    try:
        resp = requests.get(url, timeout=30)
        resp.raise_for_status()
        console.print(f"  Downloaded [dim]{len(resp.content)} bytes[/dim]")
        return resp.content
    except requests.RequestException as e:
        console.print(f"  [red]Download failed:[/red] {e}")
        return None


@click.command()
@click.option("--once", is_flag=True, help="Run a single capture cycle and exit")
def cli(once: bool):
    """Wolf Creek Pass -- SR-35 Traffic Camera Monitor"""
    try:
        settings = Settings()
    except Exception as e:
        console.print(
            Panel(
                f"[red]{e}[/red]\n\n"
                "Create a [bold].env[/bold] file with your API keys.\n"
                "See [bold].env.example[/bold] for the template.",
                title="Missing Configuration",
            )
        )
        raise SystemExit(1)

    # Run immediately
    run_capture_cycle(settings)

    if once:
        return

    # Schedule every 3 hours
    schedule.every(3).hours.do(run_capture_cycle, settings)

    console.print(
        "\n[bold]Scheduler started.[/bold] Running every 3 hours. Press Ctrl+C to stop."
    )

    try:
        while True:
            schedule.run_pending()
            time.sleep(60)
    except KeyboardInterrupt:
        console.print("\n[yellow]Shutting down...[/yellow]")


if __name__ == "__main__":
    cli()
