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
    """Show most recent captures."""
    storage = _get_storage()
    captures = storage.get_recent_captures(limit=limit)

    if not captures:
        console.print("[yellow]No captures found.[/yellow]")
        return

    table = Table(title="Recent Traffic Camera Captures")
    table.add_column("Time", style="dim")
    table.add_column("Camera", justify="right")
    table.add_column("Location")
    table.add_column("Road")

    for cap in captures:
        location = cap.location or "?"
        road = f"{cap.roadway or '?'} {cap.direction or '?'}"

        table.add_row(
            cap.captured_at,
            str(cap.camera_id),
            location,
            road,
        )

    console.print(table)


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
    table.add_column("Events", justify="right")
    table.add_column("Travel Time")

    for c in all_cycles:
        travel = ""
        if c.travel_time_s:
            mins = c.travel_time_s // 60
            travel = f"{mins} min"

        table.add_row(
            c.cycle_id,
            c.started_at,
            str(c.cameras_processed),
            str(c.event_count),
            travel,
        )

    console.print(table)


@cli.command()
def route():
    """Show current route info."""
    storage = _get_storage()
    routes = storage.get_routes()

    if not routes:
        console.print(
            "[yellow]No route stored. Run [bold]poe monitor --once[/bold] first.[/yellow]"
        )
        return

    r = routes[0]
    console.print(f"\n[bold]Route:[/bold] {r.origin}")
    console.print(f"    --> {r.destination}")
    console.print(
        f"  Distance: [bold]{r.distance_display or f'{r.distance_m / 1609.34:.1f} miles'}[/bold]"
    )
    console.print(
        f"  Duration: [bold]{r.travel_time_display or f'{r.duration_s / 60:.0f} min'}[/bold]"
    )
    if r.has_closure:
        console.print("  [red bold]Active closures on route![/red bold]")
    if r.has_conditions:
        console.print("  [yellow]Route conditions reported[/yellow]")


if __name__ == "__main__":
    cli()
