"""Tests for models.py -- Pydantic model construction and serialization."""

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


class TestCamera:
    def test_minimal(self):
        cam = Camera(Id=1)
        assert cam.Id == 1
        assert cam.Views == []
        assert cam.Latitude is None

    def test_full(self, sample_camera):
        assert sample_camera.Id == 100
        assert sample_camera.Roadway == "SR-35"
        assert len(sample_camera.Views) == 1

    def test_serialization_roundtrip(self, sample_camera):
        data = sample_camera.model_dump()
        cam2 = Camera.model_validate(data)
        assert cam2.Id == sample_camera.Id
        assert cam2.Latitude == sample_camera.Latitude


class TestCaptureRecord:
    def test_has_captured_at_default(self):
        c = CaptureRecord(camera_id=1, cycle_id="test")
        assert c.captured_at  # Should be auto-populated
        assert "T" in c.captured_at  # ISO format

    def test_full(self, sample_capture):
        assert sample_capture.roadway == "SR-35"
        assert sample_capture.camera_id == 100


class TestRoute:
    def test_defaults(self):
        r = Route(origin="A", destination="B")
        assert r.route_id == ""
        assert r.name == ""
        assert r.color == "#3b82f6"
        assert r.share_id == ""
        assert r.polyline == ""
        assert r.distance_m == 0
        assert r.has_closure is False
        assert r.has_conditions is False
        assert r.travel_time_display == ""
        assert r.distance_display == ""

    def test_full(self, sample_route):
        assert sample_route.route_id == "parleys-wolfcreek"
        assert sample_route.name == "Parley's / Wolf Creek"
        assert sample_route.distance_m == 145000
        assert sample_route.polyline != ""


class TestCycleSummary:
    def test_defaults(self):
        c = CycleSummary(cycle_id="test", started_at="2026-01-01")
        assert c.cameras_processed == 0
        assert c.event_count == 0

    def test_serialization(self, sample_cycle):
        data = sample_cycle.model_dump()
        assert data["cycle_id"] == "2026-02-07T12:00:00"
        c2 = CycleSummary.model_validate(data)
        assert c2.event_count == sample_cycle.event_count


class TestRoadCondition:
    def test_construction(self):
        c = RoadCondition(id=1, roadway_name="SR-35", road_condition="Snow Packed")
        assert c.road_condition == "Snow Packed"


class TestEvent:
    def test_construction(self):
        e = Event(id="1", event_type="construction", is_full_closure=True)
        assert e.is_full_closure is True
        assert e.latitude is None


class TestWeatherStation:
    def test_construction(self):
        w = WeatherStation(id=1, station_name="Wolf Creek Pass", air_temperature="28")
        assert w.air_temperature == "28"


class TestMountainPass:
    def test_defaults(self):
        p = MountainPass()
        assert p.id == 0
        assert p.name == ""
        assert p.closure_status == ""
        assert p.latitude is None

    def test_full(self, sample_mountain_pass):
        assert sample_mountain_pass.id == 44
        assert sample_mountain_pass.name == "SR-35 Wolf Creek Pass"
        assert sample_mountain_pass.elevation_ft == "9488"
        assert sample_mountain_pass.air_temperature == "25"
        assert sample_mountain_pass.closure_status == "OPEN"
        assert sample_mountain_pass.station_name == "SR-35 @ Wolf Creek"
        assert sample_mountain_pass.seasonal_route_name == "Route 35"

    def test_serialization_roundtrip(self, sample_mountain_pass):
        data = sample_mountain_pass.model_dump()
        p2 = MountainPass.model_validate(data)
        assert p2.name == sample_mountain_pass.name
        assert p2.closure_status == sample_mountain_pass.closure_status


class TestSnowPlow:
    def test_defaults(self):
        p = SnowPlow()
        assert p.id == 0
        assert p.name == ""
        assert p.latitude is None
        assert p.speed is None

    def test_full(self, sample_snow_plow):
        assert sample_snow_plow.id == 501
        assert sample_snow_plow.name == "Plow Unit 42"
        assert sample_snow_plow.speed == 25.0
        assert sample_snow_plow.last_updated == "2026-02-07T12:30:00"

    def test_serialization_roundtrip(self, sample_snow_plow):
        data = sample_snow_plow.model_dump()
        p2 = SnowPlow.model_validate(data)
        assert p2.id == sample_snow_plow.id
        assert p2.speed == sample_snow_plow.speed
