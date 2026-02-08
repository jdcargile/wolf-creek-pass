"""
Route planning and camera-to-route matching.

Uses Google Directions API to get the route polyline and travel time,
then filters UDOT cameras by proximity to the route using haversine distance.
"""

from __future__ import annotations

import math

import googlemaps
import polyline as polyline_codec
from rich.console import Console

from models import Camera, Route
from settings import Settings

console = Console()

EARTH_RADIUS_KM = 6371.0


def get_route(settings: Settings) -> Route:
    """Get driving route from origin to destination via Google Directions API."""
    gmaps = googlemaps.Client(key=settings.google_maps_api_key)

    result = gmaps.directions(
        origin=settings.origin,
        destination=settings.destination,
        mode="driving",
        departure_time="now",
    )

    if not result:
        console.print("[red]No route found from Google Directions API[/red]")
        return Route(origin=settings.origin, destination=settings.destination)

    leg = result[0]["legs"][0]
    overview_polyline = result[0]["overview_polyline"]["points"]

    route = Route(
        origin=settings.origin,
        destination=settings.destination,
        polyline=overview_polyline,
        distance_m=leg["distance"]["value"],
        duration_s=leg["duration"]["value"],
        duration_in_traffic_s=leg.get("duration_in_traffic", {}).get("value"),
    )

    distance_mi = route.distance_m / 1609.34
    duration_min = route.duration_s / 60
    console.print(
        f"Route: [bold]{distance_mi:.1f} miles[/bold], "
        f"[bold]{duration_min:.0f} min[/bold]"
    )
    if route.duration_in_traffic_s:
        traffic_min = route.duration_in_traffic_s / 60
        console.print(f"  With traffic: [bold]{traffic_min:.0f} min[/bold]")

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
