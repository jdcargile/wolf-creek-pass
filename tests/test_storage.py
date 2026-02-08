"""Tests for storage.py -- SQLiteStorage CRUD + helpers."""

from storage import SQLiteStorage, create_storage, _bool_to_int, _strip_none
from models import (
    Camera,
    CameraView,
    CaptureRecord,
    CycleSummary,
    Event,
    MountainPass,
    RoadCondition,
    Route,
    SnowPlow,
    WeatherStation,
)
from settings import Settings


class TestHelpers:
    def test_bool_to_int(self):
        assert _bool_to_int(True) == 1
        assert _bool_to_int(False) == 0
        assert _bool_to_int(None) is None

    def test_strip_none(self):
        assert _strip_none({"a": 1, "b": None, "c": "x"}) == {"a": 1, "c": "x"}
        assert _strip_none({}) == {}


class TestCreateStorage:
    def test_sqlite_backend(self):
        import os

        os.environ["STORAGE_BACKEND"] = "sqlite"
        settings = Settings()
        storage = create_storage(settings)
        assert isinstance(storage, SQLiteStorage)


class TestSQLiteStorageCameras:
    def test_save_and_get_cameras(self, sqlite_storage, sample_camera):
        sqlite_storage.save_camera(sample_camera)
        cameras = sqlite_storage.get_cameras()
        assert len(cameras) == 1
        assert cameras[0].Id == 100
        assert cameras[0].Roadway == "SR-35"
        assert cameras[0].Latitude == 40.3712

    def test_save_camera_upsert(self, sqlite_storage, sample_camera):
        sqlite_storage.save_camera(sample_camera)
        sample_camera.Location = "Updated Location"
        sqlite_storage.save_camera(sample_camera)
        cameras = sqlite_storage.get_cameras()
        assert len(cameras) == 1
        assert cameras[0].Location == "Updated Location"


class TestSQLiteStorageCaptures:
    def test_save_and_get_recent(self, sqlite_storage, sample_capture):
        sqlite_storage.save_capture(sample_capture)
        captures = sqlite_storage.get_recent_captures(limit=10)
        assert len(captures) == 1
        assert captures[0].camera_id == 100
        assert captures[0].has_snow is True

    def test_get_by_cycle(self, sqlite_storage, sample_capture):
        sqlite_storage.save_capture(sample_capture)
        captures = sqlite_storage.get_captures_by_cycle("2026-02-07T12:00:00")
        assert len(captures) == 1
        assert captures[0].analysis_notes == "Heavy snow on road surface"

    def test_get_by_cycle_empty(self, sqlite_storage):
        captures = sqlite_storage.get_captures_by_cycle("nonexistent")
        assert captures == []


class TestSQLiteStorageRoutes:
    def test_save_and_get_routes(self, sqlite_storage, sample_route):
        sqlite_storage.save_routes([sample_route])
        routes = sqlite_storage.get_routes()
        assert len(routes) == 1
        assert routes[0].route_id == "parleys-wolfcreek"
        assert routes[0].name == "Parley's / Wolf Creek"
        assert routes[0].origin == "Riverton, UT"
        assert routes[0].distance_m == 145000
        assert routes[0].polyline != ""

    def test_save_multiple_routes(self, sqlite_storage, sample_route):
        route2 = Route(
            route_id="provo-wolfcreek",
            name="Provo Canyon / Wolf Creek",
            color="#8b5cf6",
            origin="Riverton, UT",
            destination="Hanna, UT",
            distance_m=160000,
            duration_s=8000,
        )
        sqlite_storage.save_routes([sample_route, route2])
        routes = sqlite_storage.get_routes()
        assert len(routes) == 2
        route_ids = {r.route_id for r in routes}
        assert "parleys-wolfcreek" in route_ids
        assert "provo-wolfcreek" in route_ids

    def test_get_routes_empty(self, sqlite_storage):
        assert sqlite_storage.get_routes() == []


class TestSQLiteStorageCycles:
    def test_save_and_get_cycles(self, sqlite_storage, sample_cycle):
        sqlite_storage.save_cycle(sample_cycle)
        cycles = sqlite_storage.get_cycles()
        assert len(cycles) == 1
        assert cycles[0].cycle_id == "2026-02-07T12:00:00"
        assert cycles[0].cameras_processed == 3

    def test_multiple_cycles_ordered(self, sqlite_storage):
        c1 = CycleSummary(
            cycle_id="2026-02-07T10:00:00", started_at="2026-02-07T10:00:00"
        )
        c2 = CycleSummary(
            cycle_id="2026-02-07T12:00:00", started_at="2026-02-07T12:00:00"
        )
        sqlite_storage.save_cycle(c1)
        sqlite_storage.save_cycle(c2)
        cycles = sqlite_storage.get_cycles()
        assert len(cycles) == 2
        # Most recent first
        assert cycles[0].cycle_id == "2026-02-07T12:00:00"


class TestSQLiteStorageConditions:
    def test_save_and_get(self, sqlite_storage, sample_conditions):
        sqlite_storage.save_road_conditions("cycle-1", sample_conditions)
        conditions = sqlite_storage.get_road_conditions("cycle-1")
        assert len(conditions) == 2
        assert conditions[0].roadway_name == "SR-35 Wolf Creek"

    def test_empty_cycle(self, sqlite_storage):
        assert sqlite_storage.get_road_conditions("nonexistent") == []


class TestSQLiteStorageEvents:
    def test_save_and_get(self, sqlite_storage, sample_events):
        sqlite_storage.save_events("cycle-1", sample_events)
        events = sqlite_storage.get_events("cycle-1")
        assert len(events) == 2
        assert events[0].event_type == "construction"
        assert events[1].is_full_closure is True

    def test_empty_cycle(self, sqlite_storage):
        assert sqlite_storage.get_events("nonexistent") == []


class TestSQLiteStorageWeather:
    def test_save_and_get(self, sqlite_storage, sample_weather):
        sqlite_storage.save_weather("cycle-1", sample_weather)
        weather = sqlite_storage.get_weather("cycle-1")
        assert len(weather) == 2
        assert weather[0].station_name == "Wolf Creek Pass"
        assert weather[0].air_temperature == "28"

    def test_empty_cycle(self, sqlite_storage):
        assert sqlite_storage.get_weather("nonexistent") == []


class TestSQLiteStorageImages:
    def test_save_and_get_url(self, sqlite_storage, tmp_path):
        sqlite_storage.save_image("test.jpg", b"fake-jpeg-data")
        url = sqlite_storage.get_image_url("test.jpg")
        assert "test.jpg" in url
        # Verify file was written
        assert (tmp_path / "images" / "test.jpg").read_bytes() == b"fake-jpeg-data"


class TestSQLiteStoragePasses:
    def test_save_and_get(self, sqlite_storage, sample_mountain_passes):
        sqlite_storage.save_mountain_passes("cycle-1", sample_mountain_passes)
        passes = sqlite_storage.get_mountain_passes("cycle-1")
        assert len(passes) == 2
        assert passes[0].name == "SR-35 Wolf Creek Pass"
        assert passes[0].air_temperature == "25"
        assert passes[1].name == "I-80 Parleys Summit"

    def test_empty_cycle(self, sqlite_storage):
        assert sqlite_storage.get_mountain_passes("nonexistent") == []

    def test_full_fields(self, sqlite_storage, sample_mountain_pass):
        sqlite_storage.save_mountain_passes("cycle-1", [sample_mountain_pass])
        passes = sqlite_storage.get_mountain_passes("cycle-1")
        assert len(passes) == 1
        p = passes[0]
        assert p.id == 44
        assert p.roadway == "SR-35"
        assert p.elevation_ft == "9488"
        assert p.station_name == "SR-35 @ Wolf Creek"
        assert p.wind_speed == "15"
        assert p.wind_gust == "30"
        assert p.surface_status == "Snow/Ice"
        assert p.visibility == "0.5"
        assert p.closure_status == "OPEN"
        assert p.closure_description == "Francis to Hanna"
        assert p.seasonal_route_name == "Route 35"
        assert p.seasonal_closure_title == "SR 35 Wolf Creek Pass"
        assert "Evening" in p.forecasts


class TestSQLiteStoragePlows:
    def test_save_and_get(self, sqlite_storage, sample_snow_plows):
        sqlite_storage.save_snow_plows("cycle-1", sample_snow_plows)
        plows = sqlite_storage.get_snow_plows("cycle-1")
        assert len(plows) == 2
        assert plows[0].name == "Plow Unit 42"
        assert plows[0].speed == 25.0
        assert plows[1].name == "Plow Unit 99"

    def test_empty_cycle(self, sqlite_storage):
        assert sqlite_storage.get_snow_plows("nonexistent") == []

    def test_full_fields(self, sqlite_storage, sample_snow_plow):
        sqlite_storage.save_snow_plows("cycle-1", [sample_snow_plow])
        plows = sqlite_storage.get_snow_plows("cycle-1")
        assert len(plows) == 1
        p = plows[0]
        assert p.id == 501
        assert p.latitude == 40.37
        assert p.longitude == -111.12
        assert p.heading == 180.0
        assert p.last_updated == "2026-02-07T12:30:00"


class TestSQLiteStorageImageHashes:
    def test_save_and_get_hash(self, sqlite_storage):
        sqlite_storage.save_image_hash(100, "abc123")
        assert sqlite_storage.get_image_hash(100) == "abc123"

    def test_get_nonexistent_hash(self, sqlite_storage):
        assert sqlite_storage.get_image_hash(999) is None

    def test_upsert_hash(self, sqlite_storage):
        sqlite_storage.save_image_hash(100, "old_hash")
        sqlite_storage.save_image_hash(100, "new_hash")
        assert sqlite_storage.get_image_hash(100) == "new_hash"
