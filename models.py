"""Pydantic models for traffic camera data and UDOT API responses."""

from datetime import datetime

from pydantic import BaseModel, Field


# ---- UDOT Camera Models ----


class CameraView(BaseModel):
    """A single camera view with an image URL."""

    Url: str | None = None


class Camera(BaseModel):
    """A UDOT traffic camera."""

    Id: int
    SourceId: str | None = None
    Roadway: str | None = None
    Direction: str | None = None
    Location: str | None = None
    Latitude: float | None = None
    Longitude: float | None = None
    Views: list[CameraView] = Field(default_factory=list)
    distance_from_route_km: float | None = None


# ---- Capture Record (stored in DB) ----


class CaptureRecord(BaseModel):
    """A single camera capture record."""

    camera_id: int
    cycle_id: str
    captured_at: str = Field(default_factory=lambda: datetime.now().isoformat())
    image_key: str = ""  # S3 key or local file path
    # Denormalized camera info (for DynamoDB single-table)
    roadway: str | None = None
    direction: str | None = None
    location: str | None = None
    latitude: float | None = None
    longitude: float | None = None


# ---- Route Models ----


class Route(BaseModel):
    """A named route with encoded polyline and travel info from UDOT 511."""

    route_id: str = ""  # e.g. "parleys-wolfcreek"
    name: str = ""  # e.g. "Parley's / Wolf Creek"
    color: str = "#3b82f6"  # Hex color for map polyline
    share_id: str = ""  # UDOT 511 shared route UUID
    origin: str = ""
    destination: str = ""
    polyline: str = ""  # Google encoded polyline (from UDOT 511)
    distance_m: int = 0
    duration_s: int = 0  # UDOT posted travel time
    has_closure: bool = False  # any active closures on this route
    has_conditions: bool = False  # any active road conditions on this route
    travel_time_display: str = ""  # e.g. "1 hr 45 min"
    distance_display: str = ""  # e.g. "88.8 miles"


# ---- UDOT Road Conditions ----


class RoadCondition(BaseModel):
    """Road surface/weather conditions for a highway segment."""

    id: int = 0
    roadway_name: str = ""
    road_condition: str = ""
    weather_condition: str = ""
    restriction: str = ""
    encoded_polyline: str = ""
    last_updated: int = 0


# ---- UDOT Events ----


class Event(BaseModel):
    """Traffic event (accident, construction, closure)."""

    id: str = ""
    event_type: str = ""
    event_sub_type: str = ""
    roadway_name: str = ""
    direction: str = ""
    description: str = ""
    severity: str = ""
    latitude: float | None = None
    longitude: float | None = None
    is_full_closure: bool = False


# ---- UDOT Weather Stations ----


class WeatherStation(BaseModel):
    """Road Weather Information System station data."""

    id: int = 0
    station_name: str = ""
    air_temperature: str = ""
    surface_temp: str = ""
    surface_status: str = ""
    wind_speed_avg: str = ""
    wind_speed_gust: str = ""
    wind_direction: str = ""
    precipitation: str = ""
    relative_humidity: str = ""


# ---- Mountain Passes ----


class MountainPass(BaseModel):
    """Mountain pass conditions from UDOT API."""

    id: int = 0
    name: str = ""
    roadway: str = ""
    elevation_ft: str = ""
    latitude: float | None = None
    longitude: float | None = None
    # Weather station data
    station_name: str = ""
    air_temperature: str = ""
    wind_speed: str = ""
    wind_gust: str = ""
    wind_direction: str = ""
    surface_temp: str = ""
    surface_status: str = ""
    visibility: str = ""
    # Forecasts (pipe-delimited periods from UDOT, e.g. "Evening;...|Morning;...")
    forecasts: str = ""
    # Seasonal closure info
    closure_status: str = ""  # "OPEN", "CLOSED", or ""
    closure_description: str = ""
    seasonal_route_name: str = ""
    seasonal_closure_title: str = ""


# ---- Snow Plows ----


class SnowPlow(BaseModel):
    """A UDOT snow plow / service vehicle with real-time GPS position."""

    id: int = 0
    name: str = ""
    latitude: float | None = None
    longitude: float | None = None
    heading: float | None = None
    speed: float | None = None
    last_updated: str = ""


# ---- Capture Cycle Summary ----


class CycleSummary(BaseModel):
    """Summary of a complete capture cycle."""

    cycle_id: str
    started_at: str
    completed_at: str = ""
    cameras_processed: int = 0
    event_count: int = 0
    travel_time_s: int | None = None
    distance_m: int | None = None
