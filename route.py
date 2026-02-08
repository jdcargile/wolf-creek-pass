"""
Route planning and camera-to-route matching.

Uses UDOT 511 shared route API to get route polylines, travel times,
and per-segment conditions/events/cameras. Filters UDOT cameras by
proximity using haversine.
"""

from __future__ import annotations

import json
import math

import polyline as polyline_codec
import requests
from rich.console import Console

from models import Camera, Route
from settings import ROUTES, RouteConfig

console = Console()

EARTH_RADIUS_KM = 6371.0
UDOT_511_URL = "https://prod-ut.ibi511.com/Api/Route/GetRouteByShareID"


def get_routes() -> list[Route]:
    """Fetch all configured routes from UDOT 511 shared route API."""
    routes: list[Route] = []

    for route_cfg in ROUTES:
        try:
            route = _fetch_511_route(route_cfg)
            routes.append(route)
        except Exception as e:
            console.print(f"[yellow]Route '{route_cfg.name}' failed:[/yellow] {e}")
            routes.append(
                Route(
                    route_id=route_cfg.route_id,
                    name=route_cfg.name,
                    color=route_cfg.color,
                    share_id=route_cfg.share_id,
                )
            )

    return routes


def _fetch_511_route(route_cfg: RouteConfig) -> Route:
    """Fetch a single route from UDOT 511 shared route API."""
    if not route_cfg.share_id:
        console.print(f"[yellow]No share_id for route '{route_cfg.name}'[/yellow]")
        return Route(
            route_id=route_cfg.route_id,
            name=route_cfg.name,
            color=route_cfg.color,
        )

    resp = requests.post(
        UDOT_511_URL,
        params={"shareId": route_cfg.share_id},
        timeout=30,
    )
    resp.raise_for_status()
    data = resp.json()

    # Parse origin/destination from encodedMarkers
    origin = ""
    destination = ""
    markers_json = data.get("encodedMarkers", "")
    if markers_json:
        try:
            markers = json.loads(markers_json)
            if len(markers) >= 2:
                origin = markers[0].get("location", {}).get("Name", "")
                destination = markers[-1].get("location", {}).get("Name", "")
        except (json.JSONDecodeError, KeyError):
            pass

    # UDOT returns polyline as an array — join into one string
    polyline_parts = data.get("encodedPolyline", [])
    polyline = polyline_parts[0] if polyline_parts else ""

    # Travel time and distance
    posted_seconds = data.get("postedTravelTimeSeconds", 0)
    length_meters = data.get("lengthMeters", 0)

    # Statistics
    stats = data.get("statistics", {})
    has_closure = stats.get("hasCurrentClosure", False) or stats.get(
        "includesClosures", False
    )
    has_conditions = stats.get("includesRouteConditions", False)

    route = Route(
        route_id=route_cfg.route_id,
        name=route_cfg.name,
        color=route_cfg.color,
        share_id=route_cfg.share_id,
        origin=origin,
        destination=destination,
        polyline=polyline,
        distance_m=int(length_meters),
        duration_s=int(posted_seconds),
        has_closure=has_closure,
        has_conditions=has_conditions,
        travel_time_display=stats.get("travelTimeDisplay", ""),
        distance_display=stats.get("lengthDisplay", ""),
    )

    console.print(
        f"Route [bold]{route_cfg.name}[/bold]: "
        f"[bold]{route.distance_display}[/bold], "
        f"[bold]{route.travel_time_display}[/bold]"
    )
    if has_closure:
        console.print("  [red bold]Active closures on route![/red bold]")
    if has_conditions:
        console.print("  [yellow]Route conditions reported[/yellow]")

    return route


def decode_route_points(route: Route) -> list[tuple[float, float]]:
    """Decode a Google encoded polyline into a list of (lat, lng) tuples."""
    if not route.polyline:
        return []
    return polyline_codec.decode(route.polyline)


def haversine_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Calculate the great-circle distance between two points in km."""
    lat1_r, lon1_r = math.radians(lat1), math.radians(lon1)
    lat2_r, lon2_r = math.radians(lat2), math.radians(lon2)

    dlat = lat2_r - lat1_r
    dlon = lon2_r - lon1_r

    a = (
        math.sin(dlat / 2) ** 2
        + math.cos(lat1_r) * math.cos(lat2_r) * math.sin(dlon / 2) ** 2
    )
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))

    return EARTH_RADIUS_KM * c


def min_distance_to_route(
    lat: float, lon: float, route_points: list[tuple[float, float]]
) -> float:
    """Find the minimum distance (km) from a point to any point on the route."""
    if not route_points:
        return float("inf")
    return min(haversine_km(lat, lon, rlat, rlon) for rlat, rlon in route_points)


def filter_cameras_by_route(
    cameras: list[Camera],
    route: Route,
    buffer_km: float = 2.0,
) -> list[Camera]:
    """Filter cameras to only those within buffer_km of the route.

    Returns cameras sorted by their position along the route (roughly).
    Each camera gets its `distance_from_route_km` field populated.
    """
    route_points = decode_route_points(route)
    if not route_points:
        console.print("[yellow]No route points to filter against[/yellow]")
        return cameras

    matched: list[tuple[float, int, Camera]] = []

    for camera in cameras:
        if camera.Latitude is None or camera.Longitude is None:
            continue

        dist = min_distance_to_route(camera.Latitude, camera.Longitude, route_points)

        if dist <= buffer_km:
            camera.distance_from_route_km = round(dist, 3)

            # Find the closest route point index for sorting by position along route
            closest_idx = min(
                range(len(route_points)),
                key=lambda i: haversine_km(
                    camera.Latitude,
                    camera.Longitude,  # type: ignore[arg-type]
                    route_points[i][0],
                    route_points[i][1],
                ),
            )
            matched.append((dist, closest_idx, camera))

    # Sort by position along route (closest_idx)
    matched.sort(key=lambda x: x[1])

    console.print(
        f"Matched [bold]{len(matched)}[/bold] cameras within "
        f"{buffer_km}km of route (out of {len(cameras)} total)"
    )

    return [cam for _, _, cam in matched]
