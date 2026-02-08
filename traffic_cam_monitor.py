#!/usr/bin/env python3
"""
Wolf Creek Pass -- Route-Aware Traffic Camera Monitor

Orchestrates the full capture cycle:
1. Get route (Google Directions API)
2. Fetch cameras along route (UDOT API + haversine filtering)
3. Download + analyze camera images (Claude Vision)
4. Fetch road conditions, events, weather (UDOT API)
5. Store everything (DynamoDB or SQLite)
6. Export JSON for Vue frontend
"""

import hashlib
import time
from datetime import datetime

import anthropic
import click
import requests
import schedule
from rich.console import Console
from rich.panel import Panel

from analyze import analyze_image_bytes
from export import export_cycle_index, export_cycle_to_file
from models import CaptureRecord, CycleSummary
from route import get_route
from settings import Settings
from storage import create_storage
from udot import (
    fetch_route_cameras,
    fetch_route_conditions,
    fetch_route_events,
    fetch_route_weather,
)

console = Console()


def run_capture_cycle(settings: Settings) -> None:
    """Run one complete capture cycle."""
    storage = create_storage(settings)
    storage.init()

    cycle_id = datetime.now().strftime("%Y-%m-%dT%H:%M:%S")
    cycle = CycleSummary(cycle_id=cycle_id, started_at=cycle_id)

    console.rule(f"[bold blue]Capture cycle {cycle_id}[/bold blue]")

    # 1. Get route
    route = None
    if settings.google_maps_api_key:
        try:
            route = get_route(settings)
            storage.save_route(route)
        except Exception as e:
            console.print(
                f"[yellow]Route fetch failed (continuing without):[/yellow] {e}"
            )
            route = storage.get_route()  # Fall back to cached route
    else:
        console.print("[yellow]No Google Maps API key -- skipping route[/yellow]")
        route = storage.get_route()

    # 2. Fetch cameras along route
    if route and route.polyline:
        cameras = fetch_route_cameras(
            settings.udot_api_key, route, settings.camera_buffer_km
        )
    else:
        # Fallback: fetch all cameras, no route filtering
        from udot import fetch_all_cameras

        cameras = fetch_all_cameras(settings.udot_api_key)

    # 3. Download images + analyze with Claude Vision
    vision_client = anthropic.Anthropic(api_key=settings.anthropic_api_key)
    snow_count = 0
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

        # Check image hash -- skip analysis if unchanged from last cycle
        image_hash = hashlib.sha256(image_data).hexdigest()
        prev_hash = storage.get_image_hash(camera.Id)

        if prev_hash == image_hash:
            # Image unchanged -- reuse previous analysis
            console.print("  [dim]Image unchanged -- skipping analysis[/dim]")
            skipped_count += 1
            prev_captures = storage.get_recent_captures(limit=100)
            prev = next((c for c in prev_captures if c.camera_id == camera.Id), None)
            capture = CaptureRecord(
                camera_id=camera.Id,
                cycle_id=cycle_id,
                image_key=prev.image_key if prev else "",
                has_snow=prev.has_snow if prev else None,
                has_car=prev.has_car if prev else None,
                has_truck=prev.has_truck if prev else None,
                has_animal=prev.has_animal if prev else None,
                analysis_notes=(prev.analysis_notes if prev else "") + " [cached]",
                roadway=camera.Roadway,
                direction=camera.Direction,
                location=camera.Location,
                latitude=camera.Latitude,
                longitude=camera.Longitude,
            )
            storage.save_capture(capture)
            if capture.has_snow:
                snow_count += 1
            continue

        # New image -- save and analyze
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        image_key = f"cam_{camera.Id}_{timestamp}.jpg"
        storage.save_image(image_key, image_data)
        storage.save_image_hash(camera.Id, image_hash)

        # Analyze with Claude Vision
        analysis = analyze_image_bytes(vision_client, image_data)

        # Build capture record (denormalized)
        capture = CaptureRecord(
            camera_id=camera.Id,
            cycle_id=cycle_id,
            image_key=image_key,
            has_snow=analysis.has_snow,
            has_car=analysis.has_car,
            has_truck=analysis.has_truck,
            has_animal=analysis.has_animal,
            analysis_notes=analysis.notes,
            roadway=camera.Roadway,
            direction=camera.Direction,
            location=camera.Location,
            latitude=camera.Latitude,
            longitude=camera.Longitude,
        )
        storage.save_capture(capture)

        if analysis.has_snow:
            snow_count += 1

        # Display results
        snow = "[red]SNOW[/red]" if analysis.has_snow else "[green]Clear[/green]"
        cars = "Cars" if analysis.has_car else ""
        trucks = "Trucks" if analysis.has_truck else ""
        animals = "[yellow]ANIMALS[/yellow]" if analysis.has_animal else ""
        flags = " | ".join(f for f in [snow, cars, trucks, animals] if f)
        console.print(f"  {flags}")
        if analysis.notes:
            console.print(f"  [dim]{analysis.notes}[/dim]")

    # 4. Fetch UDOT enrichment data
    if route:
        conditions = fetch_route_conditions(settings.udot_api_key, route)
        storage.save_road_conditions(cycle_id, conditions)
        console.print(f"Saved [bold]{len(conditions)}[/bold] road conditions")

        events = fetch_route_events(settings.udot_api_key, route)
        storage.save_events(cycle_id, events)
        console.print(f"Saved [bold]{len(events)}[/bold] events")

        weather = fetch_route_weather(settings.udot_api_key, route)
        storage.save_weather(cycle_id, weather)
        console.print(f"Saved [bold]{len(weather)}[/bold] weather stations")
    else:
        conditions, events, weather = [], [], []

    # 5. Save cycle summary
    cycle.completed_at = datetime.now().isoformat()
    cycle.cameras_processed = len(cameras)
    cycle.snow_count = snow_count
    cycle.event_count = len(events)
    cycle.travel_time_s = (
        route.duration_in_traffic_s or route.duration_s if route else None
    )
    cycle.distance_m = route.distance_m if route else None
    storage.save_cycle(cycle)

    # 6. Export JSON for Vue
    export_cycle_to_file(storage, cycle, route, settings)
    export_cycle_index(storage, settings)

    analyzed = len(cameras) - skipped_count
    console.rule(
        f"[bold blue]Cycle complete -- {len(cameras)} cameras, "
        f"{analyzed} analyzed, {skipped_count} cached, "
        f"{snow_count} with snow[/bold blue]"
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
