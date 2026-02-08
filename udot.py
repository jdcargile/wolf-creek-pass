"""
UDOT Traffic API client.

Fetches all data from the UDOT API and filters by proximity to the route.
Rate limit: 10 calls per 60 seconds. All endpoints return ALL records (no server-side filtering).
"""

from __future__ import annotations

import requests
from rich.console import Console

from models import (
    Camera,
    CameraView,
    Event,
    MountainPass,
    RoadCondition,
    SnowPlow,
    WeatherStation,
)
from route import (
    filter_cameras_by_route,
    min_distance_to_route,
    decode_route_points,
    Route,
)

console = Console()

BASE_URL = "https://www.udottraffic.utah.gov/api/v2/get"
TIMEOUT = 30


def _fetch(endpoint: str, api_key: str) -> list[dict]:
    """Fetch data from a UDOT API endpoint."""
    url = f"{BASE_URL}/{endpoint}"
    params = {"key": api_key, "format": "json"}

    try:
        resp = requests.get(url, params=params, timeout=TIMEOUT)
        resp.raise_for_status()
        data = resp.json()
        if isinstance(data, list):
            return data
        return []
    except requests.RequestException as e:
        console.print(f"[red]UDOT API error ({endpoint}):[/red] {e}")
        return []


# ---- Cameras ----


def fetch_all_cameras(api_key: str) -> list[Camera]:
    """Fetch all UDOT cameras."""
    raw = _fetch("cameras", api_key)
    cameras = []
    for item in raw:
        views = [CameraView(Url=v.get("Url")) for v in item.get("Views", [])]
        cameras.append(
            Camera(
                Id=item.get("Id", 0),
                SourceId=item.get("SourceId"),
                Roadway=item.get("Roadway"),
                Direction=item.get("Direction"),
                Location=item.get("Location"),
                Latitude=item.get("Latitude"),
                Longitude=item.get("Longitude"),
                Views=views,
            )
        )
    console.print(f"Fetched [bold]{len(cameras)}[/bold] total UDOT cameras")
    return cameras


def fetch_route_cameras(
    api_key: str, route: Route, buffer_km: float = 2.0
) -> list[Camera]:
    """Fetch all cameras and filter to those near the route."""
    all_cameras = fetch_all_cameras(api_key)
    return filter_cameras_by_route(all_cameras, route, buffer_km)


# ---- Road Conditions ----


def fetch_road_conditions(api_key: str) -> list[RoadCondition]:
    """Fetch all road conditions."""
    raw = _fetch("roadconditions", api_key)
    return [
        RoadCondition(
            id=item.get("Id", 0),
            roadway_name=item.get("RoadwayName", ""),
            road_condition=item.get("RoadCondition", ""),
            weather_condition=item.get("WeatherCondition", ""),
            restriction=item.get("Restriction", ""),
            encoded_polyline=item.get("EncodedPolyline", ""),
            last_updated=item.get("LastUpdated", 0),
        )
        for item in raw
    ]


def fetch_route_conditions(
    api_key: str, route: Route, buffer_km: float = 10.0
) -> list[RoadCondition]:
    """Fetch road conditions and filter to those whose names match route roadways."""
    all_conditions = fetch_road_conditions(api_key)
    # Filter by roadway name keywords along the route
    route_roads = {"i-15", "us-189", "us-40", "sr-35", "sr-32", "us-6"}
    return [
        c
        for c in all_conditions
        if any(road in c.roadway_name.lower() for road in route_roads)
    ]


# ---- Events ----


def fetch_events(api_key: str) -> list[Event]:
    """Fetch all traffic events (accidents, construction, closures)."""
    raw = _fetch("event", api_key)
    return [
        Event(
            id=str(item.get("ID", "")),
            event_type=item.get("EventType", ""),
            event_sub_type=item.get("EventSubType", ""),
            roadway_name=item.get("RoadwayName", ""),
            direction=item.get("DirectionOfTravel", ""),
            description=item.get("Description", ""),
            severity=item.get("Severity", ""),
            latitude=item.get("Latitude"),
            longitude=item.get("Longitude"),
            is_full_closure=bool(item.get("IsFullClosure", False)),
        )
        for item in raw
    ]


def fetch_route_events(
    api_key: str, route: Route, buffer_km: float = 5.0
) -> list[Event]:
    """Fetch events and filter to those near the route."""
    all_events = fetch_events(api_key)
    route_points = decode_route_points(route)
    if not route_points:
        return all_events

    return [
        e
        for e in all_events
        if e.latitude is not None
        and e.longitude is not None
        and min_distance_to_route(e.latitude, e.longitude, route_points) <= buffer_km
    ]


# ---- Weather Stations ----


def fetch_weather_stations(api_key: str) -> list[WeatherStation]:
    """Fetch all weather station data."""
    raw = _fetch("weatherstations", api_key)
    return [
        WeatherStation(
            id=item.get("Id", 0),
            station_name=item.get("StationName", ""),
            air_temperature=item.get("AirTemperature", ""),
            surface_temp=item.get("SurfaceTemp", ""),
            surface_status=item.get("SurfaceStatus", ""),
            wind_speed_avg=item.get("WindSpeedAvg", ""),
            wind_speed_gust=item.get("WindSpeedGust", ""),
            wind_direction=item.get("WindDirection", ""),
            precipitation=item.get("Precipitation", ""),
            relative_humidity=item.get("RelativeHumidity", ""),
        )
        for item in raw
    ]


def fetch_route_weather(
    api_key: str, route: Route, buffer_km: float = 10.0
) -> list[WeatherStation]:
    """Fetch weather stations near the route.

    Weather stations don't have lat/lng in the API, so we filter by name keywords.
    """
    all_stations = fetch_weather_stations(api_key)
    # Known stations along/near this route
    route_keywords = {
        "wolf creek",
        "daniels",
        "heber",
        "provo canyon",
        "strawberry",
        "deer creek",
        "parleys",
        "spanish fork",
        "us-40",
        "sr-35",
        "duchesne",
        "currant creek",
    }
    return [
        s
        for s in all_stations
        if any(kw in s.station_name.lower() for kw in route_keywords)
    ]


# ---- Mountain Passes ----


# Passes along JD's routes (by keyword in the UDOT pass name)
ROUTE_PASS_KEYWORDS = {
    "wolf creek",
    "parley",
    "daniels",
    "provo canyon",
    "mayflower",
    "sr-248",
    "pinion",
}


def _parse_mountain_pass(item: dict) -> MountainPass:
    """Parse a single UDOT mountain pass dict into a MountainPass model."""
    seasonal_info = item.get("SeasonalInfo") or []
    closure_status = ""
    closure_desc = ""
    if seasonal_info:
        closure_status = seasonal_info[0].get("SeasonalClosureStatus", "")
        closure_desc = seasonal_info[0].get("SeasonalClosureDescription", "")

    return MountainPass(
        id=item.get("Id", 0),
        name=item.get("Name", ""),
        roadway=item.get("Roadway", ""),
        elevation_ft=item.get("MaxElevation", ""),
        latitude=item.get("Latitude"),
        longitude=item.get("Longitude"),
        air_temperature=item.get("AirTemperature") or "",
        wind_speed=item.get("WindSpeed") or "",
        wind_gust=item.get("WindGust") or "",
        wind_direction=item.get("WindDirection") or "",
        surface_temp=item.get("SurfaceTemp") or "",
        surface_status=item.get("SurfaceStatus") or "",
        visibility=item.get("Visibility") or "",
        forecasts=item.get("Forecasts") or "",
        closure_status=closure_status,
        closure_description=closure_desc,
    )


def fetch_all_mountain_passes(api_key: str) -> list[MountainPass]:
    """Fetch all mountain passes from UDOT."""
    raw = _fetch("mountainpasses", api_key)
    return [_parse_mountain_pass(item) for item in raw]


def fetch_route_passes(api_key: str) -> list[MountainPass]:
    """Fetch mountain passes along JD's routes."""
    all_passes = fetch_all_mountain_passes(api_key)
    return [
        p for p in all_passes if any(kw in p.name.lower() for kw in ROUTE_PASS_KEYWORDS)
    ]


def is_wolf_creek_closed(api_key: str) -> bool:
    """Check if Wolf Creek Pass (SR-35) is currently closed."""
    all_passes = fetch_all_mountain_passes(api_key)
    for p in all_passes:
        if "wolf creek" in p.name.lower():
            if p.closure_status.upper() == "CLOSED":
                console.print("[red bold]Wolf Creek Pass is CLOSED[/red bold]")
                return True
            console.print(
                f"Wolf Creek Pass status: [green]{p.closure_status or 'OPEN'}[/green]"
            )
            return False
    console.print("[yellow]Wolf Creek Pass not found in UDOT data[/yellow]")
    return False


# ---- Alerts ----


def fetch_alerts(api_key: str) -> list[dict]:
    """Fetch system-wide traffic alerts."""
    return _fetch("alerts", api_key)


# ---- Snow Plows ----


def fetch_all_snow_plows(api_key: str) -> list[SnowPlow]:
    """Fetch all real-time snow plow positions."""
    raw = _fetch("servicevehicles", api_key)
    return [
        SnowPlow(
            id=item.get("Id", 0),
            name=item.get("Name", ""),
            latitude=item.get("Latitude"),
            longitude=item.get("Longitude"),
            heading=item.get("Heading"),
            speed=item.get("Speed"),
            last_updated=item.get("LastUpdated", ""),
        )
        for item in raw
    ]


def fetch_route_plows(
    api_key: str, routes: list[Route], buffer_km: float = 10.0
) -> list[SnowPlow]:
    """Fetch snow plows near any of the given routes."""
    all_plows = fetch_all_snow_plows(api_key)
    if not all_plows:
        return []

    # Build a combined set of route points from all routes
    all_route_points: list[tuple[float, float]] = []
    for route in routes:
        all_route_points.extend(decode_route_points(route))

    if not all_route_points:
        return all_plows

    return [
        p
        for p in all_plows
        if p.latitude is not None
        and p.longitude is not None
        and min_distance_to_route(p.latitude, p.longitude, all_route_points)
        <= buffer_km
    ]
