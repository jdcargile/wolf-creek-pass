"""
Route planning and camera-to-route matching.

Uses Google Directions API to get route polylines and travel times for
multiple named routes. Filters UDOT cameras by proximity using haversine.
"""

from __future__ import annotations

import math

import googlemaps
import polyline as polyline_codec
from rich.console import Console

from models import Camera, Route
from settings import ROUTES, RouteConfig, Settings

console = Console()

EARTH_RADIUS_KM = 6371.0


def get_routes(settings: Settings) -> list[Route]:
    """Fetch all configured routes from Google Directions API."""
    gmaps = googlemaps.Client(key=settings.google_maps_api_key)
    routes: list[Route] = []

    for route_cfg in ROUTES:
        try:
            route = _fetch_single_route(gmaps, settings, route_cfg)
            routes.append(route)
        except Exception as e:
            console.print(f"[yellow]Route '{route_cfg.name}' failed:[/yellow] {e}")
            # Return a stub so the route still appears in the data
            routes.append(
                Route(
                    route_id=route_cfg.route_id,
                    name=route_cfg.name,
                    color=route_cfg.color,
                    origin=settings.origin,
                    destination=settings.destination,
                )
            )

    return routes


def _fetch_single_route(
    gmaps: googlemaps.Client,
    settings: Settings,
    route_cfg: RouteConfig,
) -> Route:
    """Fetch a single route with waypoints from Google Directions API."""
    kwargs: dict = {
        "origin": settings.origin,
        "destination": settings.destination,
        "mode": "driving",
        "departure_time": "now",
    }

    if route_cfg.waypoints:
        kwargs["waypoints"] = [f"via:{wp}" for wp in route_cfg.waypoints]

    result = gmaps.directions(**kwargs)

    if not result:
        console.print(f"[red]No result for route '{route_cfg.name}'[/red]")
        return Route(
            route_id=route_cfg.route_id,
            name=route_cfg.name,
            color=route_cfg.color,
            origin=settings.origin,
            destination=settings.destination,
        )

    leg = result[0]["legs"][0]
    overview_polyline = result[0]["overview_polyline"]["points"]

    # When using waypoints, sum all legs for total distance/duration
    total_distance = sum(l["distance"]["value"] for l in result[0]["legs"])
    total_duration = sum(l["duration"]["value"] for l in result[0]["legs"])
    total_traffic = None
    if all("duration_in_traffic" in l for l in result[0]["legs"]):
        total_traffic = sum(
            l["duration_in_traffic"]["value"] for l in result[0]["legs"]
        )

    route = Route(
        route_id=route_cfg.route_id,
        name=route_cfg.name,
        color=route_cfg.color,
        origin=settings.origin,
        destination=settings.destination,
        polyline=overview_polyline,
        distance_m=total_distance,
        duration_s=total_duration,
        duration_in_traffic_s=total_traffic,
    )

    distance_mi = route.distance_m / 1609.34
    duration_min = route.duration_s / 60
    console.print(
        f"Route [bold]{route_cfg.name}[/bold]: "
        f"[bold]{distance_mi:.1f} mi[/bold], "
        f"[bold]{duration_min:.0f} min[/bold]"
    )
    if route.duration_in_traffic_s:
        traffic_min = route.duration_in_traffic_s / 60
        console.print(f"  With traffic: [bold]{traffic_min:.0f} min[/bold]")

    return route


# Keep backward-compat for tests that call get_route()
def get_route(settings: Settings) -> Route:
    """Get the primary route. Deprecated -- use get_routes() instead."""
    routes = get_routes(settings)
    return (
        routes[0]
        if routes
        else Route(origin=settings.origin, destination=settings.destination)
    )


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
