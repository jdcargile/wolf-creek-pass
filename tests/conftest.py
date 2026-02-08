"""Shared test fixtures."""

import os

import pytest

from models import (
    Camera,
    CameraView,
    CaptureRecord,
    CycleSummary,
    Event,
    RoadCondition,
    Route,
    WeatherStation,
)

# Ensure settings can be constructed without a real .env
os.environ.setdefault("UDOT_API_KEY", "test-key")
os.environ.setdefault("ANTHROPIC_API_KEY", "test-key")
os.environ.setdefault("STORAGE_BACKEND", "sqlite")


@pytest.fixture
def sample_camera():
    return Camera(
        Id=100,
        Roadway="SR-35",
        Direction="NB",
        Location="Wolf Creek Pass Summit",
        Latitude=40.3712,
        Longitude=-111.1156,
        Views=[CameraView(Url="http://example.com/cam100.jpg")],
    )


@pytest.fixture
def sample_cameras():
    """Cameras at known positions near and far from a route."""
    return [
        Camera(
            Id=1,
            Roadway="SR-35",
            Direction="NB",
            Location="Near Route",
            Latitude=40.37,
            Longitude=-111.12,
            Views=[CameraView(Url="http://a.com/1.jpg")],
        ),
        Camera(
            Id=2,
            Roadway="I-15",
            Direction="SB",
            Location="Far Away",
            Latitude=38.0,
            Longitude=-109.0,
            Views=[CameraView(Url="http://a.com/2.jpg")],
        ),
        Camera(
            Id=3,
            Roadway="US-40",
            Direction="EB",
            Location="Also Near",
            Latitude=40.38,
            Longitude=-111.10,
            Views=[CameraView(Url="http://a.com/3.jpg")],
        ),
        Camera(Id=4, Location="No coords", Views=[]),  # No lat/lon
    ]


@pytest.fixture
def sample_route():
    """Route with a polyline near Wolf Creek Pass area."""
    # Encoded polyline for a short segment near (40.37, -111.12)
    import polyline as polyline_codec

    points = [(40.36, -111.14), (40.37, -111.12), (40.38, -111.10), (40.39, -111.08)]
    encoded = polyline_codec.encode(points)
    return Route(
        route_id="parleys-wolfcreek",
        name="Parley's / Wolf Creek",
        color="#3b82f6",
        origin="Riverton, UT",
        destination="Hanna, UT",
        polyline=encoded,
        distance_m=145000,
        duration_s=7200,
    )


@pytest.fixture
def sample_capture():
    return CaptureRecord(
        camera_id=100,
        cycle_id="2026-02-07T12:00:00",
        image_key="cam_100_20260207_120000.jpg",
        has_snow=True,
        has_car=True,
        has_truck=False,
        has_animal=False,
        analysis_notes="Heavy snow on road surface",
        roadway="SR-35",
        direction="NB",
        location="Wolf Creek Pass Summit",
        latitude=40.3712,
        longitude=-111.1156,
    )


@pytest.fixture
def sample_cycle():
    return CycleSummary(
        cycle_id="2026-02-07T12:00:00",
        started_at="2026-02-07T12:00:00",
        completed_at="2026-02-07T12:05:00",
        cameras_processed=3,
        snow_count=1,
        event_count=2,
        travel_time_s=7200,
        distance_m=145000,
    )


@pytest.fixture
def sample_conditions():
    return [
        RoadCondition(
            id=1,
            roadway_name="SR-35 Wolf Creek",
            road_condition="Snow Packed",
            weather_condition="Snowing",
        ),
        RoadCondition(
            id=2,
            roadway_name="US-40 Heber to Duchesne",
            road_condition="Dry",
            weather_condition="Clear",
        ),
    ]


@pytest.fixture
def sample_events():
    return [
        Event(
            id="1001",
            event_type="construction",
            roadway_name="SR-35",
            direction="NB",
            description="Road work ahead",
            latitude=40.37,
            longitude=-111.12,
            is_full_closure=False,
        ),
        Event(
            id="1002",
            event_type="accidentsAndIncidents",
            roadway_name="I-15",
            direction="SB",
            description="Multi-vehicle accident",
            latitude=40.5,
            longitude=-111.9,
            is_full_closure=True,
        ),
    ]


@pytest.fixture
def sample_weather():
    return [
        WeatherStation(
            id=1,
            station_name="Wolf Creek Pass",
            air_temperature="28",
            surface_status="Snow/Ice",
        ),
        WeatherStation(
            id=2,
            station_name="Daniels Summit",
            air_temperature="32",
            surface_status="Wet",
        ),
    ]


@pytest.fixture
def sqlite_storage(tmp_path):
    """A fresh SQLiteStorage in a temp directory."""
    from storage import SQLiteStorage

    storage = SQLiteStorage(
        db_path=str(tmp_path / "test.db"),
        images_dir=str(tmp_path / "images"),
    )
    storage.init()
    return storage
