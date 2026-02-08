"""Tests for models.py -- Pydantic model construction and serialization."""

from models import (
    AnalysisResult,
    Camera,
    CameraView,
    CaptureRecord,
    CycleSummary,
    Event,
    RoadCondition,
    Route,
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


class TestAnalysisResult:
    def test_defaults(self):
        r = AnalysisResult()
        assert r.has_snow is None
        assert r.notes == ""

    def test_explicit(self):
        r = AnalysisResult(has_snow=True, has_car=False, notes="test")
        assert r.has_snow is True
        assert r.has_car is False


class TestCaptureRecord:
    def test_has_captured_at_default(self):
        c = CaptureRecord(camera_id=1, cycle_id="test")
        assert c.captured_at  # Should be auto-populated
        assert "T" in c.captured_at  # ISO format

    def test_full(self, sample_capture):
        assert sample_capture.has_snow is True
        assert sample_capture.roadway == "SR-35"


class TestRoute:
    def test_defaults(self):
        r = Route(origin="A", destination="B")
        assert r.polyline == ""
        assert r.distance_m == 0
        assert r.duration_in_traffic_s is None

    def test_full(self, sample_route):
        assert sample_route.distance_m == 145000
        assert sample_route.polyline != ""


class TestCycleSummary:
    def test_defaults(self):
        c = CycleSummary(cycle_id="test", started_at="2026-01-01")
        assert c.cameras_processed == 0
        assert c.snow_count == 0

    def test_serialization(self, sample_cycle):
        data = sample_cycle.model_dump()
        assert data["cycle_id"] == "2026-02-07T12:00:00"
        c2 = CycleSummary.model_validate(data)
        assert c2.snow_count == sample_cycle.snow_count


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
