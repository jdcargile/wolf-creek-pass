#!/usr/bin/env python3
"""
Query captured traffic camera data via the storage abstraction.
"""

import click
from rich.console import Console
from rich.table import Table

from settings import Settings
from storage import create_storage

console = Console()

ASCII_RACE_CAR = r"""
       __
  _.-'`  `'-._
 /   .-'`'-.  \
|   /  (\)  \  |
 \  '-._o_.-'  /
  '._  ___  _.'
  .--''   ''---.
 /  __|   |__  \
|  (__O   O__)  |
 \     \_/     /
  '-._______.-'
"""


def _get_storage():
    """Create storage from settings."""
    try:
        settings = Settings()
    except Exception:
        # Fallback to SQLite if no .env
        from storage import SQLiteStorage

        return SQLiteStorage()
    return create_storage(settings)


@click.group(invoke_without_command=True)
@click.pass_context
def cli(ctx):
    """Wolf Creek Pass -- Query traffic camera data."""
    if ctx.invoked_subcommand is None:
        ctx.invoke(recent)


@cli.command()
@click.option("--limit", "-n", default=20, help="Number of captures to show")
def recent(limit: int):
    """Show most recent captures with analysis results."""
    storage = _get_storage()
    captures = storage.get_recent_captures(limit=limit)

    if not captures:
        console.print("[yellow]No captures found.[/yellow]")
        return

    table = Table(title="Recent Traffic Camera Captures")
    table.add_column("Time", style="dim")
    table.add_column("Location")
    table.add_column("Snow", justify="center")
    table.add_column("Cars", justify="center")
    table.add_column("Trucks", justify="center")
    table.add_column("Animals", justify="center")
    table.add_column("Notes", max_width=40)

    cars_detected = False

    for cap in captures:
        snow = "[red]YES[/red]" if cap.has_snow else "[green]No[/green]"
        cars = "[bold]YES[/bold]" if cap.has_car else "No"
        trucks = "[bold]YES[/bold]" if cap.has_truck else "No"
        animals = "[yellow]YES[/yellow]" if cap.has_animal else "No"
        location = (
            f"{cap.location or '?'} ({cap.roadway or '?'} {cap.direction or '?'})"
        )

        if cap.has_car:
            cars_detected = True

        table.add_row(
            cap.captured_at,
            location,
            snow,
            cars,
            trucks,
            animals,
            cap.analysis_notes or "",
        )

    console.print(table)

    if cars_detected:
        console.print(ASCII_RACE_CAR, style="bold cyan")


@cli.command()
def cycles():
    """Show capture cycle history."""
    storage = _get_storage()
    all_cycles = storage.get_cycles(limit=20)

    if not all_cycles:
        console.print("[yellow]No capture cycles found.[/yellow]")
        return

    table = Table(title="Capture Cycles")
    table.add_column("Cycle ID", style="bold")
    table.add_column("Started")
    table.add_column("Cameras", justify="right")
    table.add_column("Snow", justify="right")
    table.add_column("Events", justify="right")
    table.add_column("Travel Time")

    for c in all_cycles:
        travel = ""
        if c.travel_time_s:
            mins = c.travel_time_s // 60
            travel = f"{mins} min"

        snow_style = "red" if c.snow_count > 0 else "green"

        table.add_row(
            c.cycle_id,
            c.started_at,
            str(c.cameras_processed),
            f"[{snow_style}]{c.snow_count}[/{snow_style}]",
            str(c.event_count),
            travel,
        )

    console.print(table)


@cli.command()
def route():
    """Show current route info."""
    storage = _get_storage()
    r = storage.get_route()

    if not r:
        console.print(
            "[yellow]No route stored. Run [bold]poe monitor --once[/bold] first.[/yellow]"
        )
        return

    distance_mi = r.distance_m / 1609.34
    duration_min = r.duration_s / 60

    console.print(f"\n[bold]Route:[/bold] {r.origin}")
    console.print(f"    --> {r.destination}")
    console.print(f"  Distance: [bold]{distance_mi:.1f} miles[/bold]")
    console.print(f"  Duration: [bold]{duration_min:.0f} min[/bold]")

    if r.duration_in_traffic_s:
        traffic_min = r.duration_in_traffic_s / 60
        console.print(f"  With traffic: [bold]{traffic_min:.0f} min[/bold]")


@cli.command()
def snow():
    """Show snow conditions from the latest cycle."""
    storage = _get_storage()
    all_cycles = storage.get_cycles(limit=1)

    if not all_cycles:
        console.print("[yellow]No data yet.[/yellow]")
        return

    latest = all_cycles[0]
    captures = storage.get_captures_by_cycle(latest.cycle_id)

    snow_captures = [c for c in captures if c.has_snow]

    if not snow_captures:
        console.print(f"[green]No snow detected in cycle {latest.cycle_id}[/green]")
        return

    table = Table(title=f"Snow Detections -- Cycle {latest.cycle_id}")
    table.add_column("Camera")
    table.add_column("Location")
    table.add_column("Notes", max_width=50)

    for cap in snow_captures:
        table.add_row(
            str(cap.camera_id),
            f"{cap.location or '?'} ({cap.roadway or '?'})",
            cap.analysis_notes or "",
        )

    console.print(table)
    console.print(
        f"\n[red]{len(snow_captures)}[/red] of {len(captures)} cameras detecting snow"
    )


@cli.command()
def animals():
    """Show animal sightings from the latest cycle."""
    storage = _get_storage()
    all_cycles = storage.get_cycles(limit=1)

    if not all_cycles:
        console.print("[yellow]No data yet.[/yellow]")
        return

    latest = all_cycles[0]
    captures = storage.get_captures_by_cycle(latest.cycle_id)

    animal_captures = [c for c in captures if c.has_animal]

    if not animal_captures:
        console.print(f"[green]No animal sightings in cycle {latest.cycle_id}[/green]")
        return

    table = Table(title=f"Animal Sightings -- Cycle {latest.cycle_id}")
    table.add_column("Camera")
    table.add_column("Location")
    table.add_column("Notes", max_width=50)

    for cap in animal_captures:
        table.add_row(
            str(cap.camera_id),
            f"{cap.location or '?'} ({cap.roadway or '?'})",
            cap.analysis_notes or "",
        )

    console.print(table)


if __name__ == "__main__":
    cli()
