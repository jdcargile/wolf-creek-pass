"""Tests for export.py -- JSON export to local filesystem."""

import json
from unittest.mock import patch

from export import (
    export_cycle_json,
    export_cycle_to_file,
    export_cycle_index,
    _capture_to_dict,
)
from models import CaptureRecord, CycleSummary
from settings import Settings


class TestExportCycleJson:
    def test_structure(
        self,
        sqlite_storage,
        sample_cycle,
        sample_capture,
        sample_route,
        sample_conditions,
        sample_events,
        sample_weather,
    ):
        """Verify the JSON payload has all expected top-level keys."""
        sqlite_storage.save_cycle(sample_cycle)
        sqlite_storage.save_capture(sample_capture)
        sqlite_storage.save_routes([sample_route])
        sqlite_storage.save_road_conditions(sample_cycle.cycle_id, sample_conditions)
        sqlite_storage.save_events(sample_cycle.cycle_id, sample_events)
        sqlite_storage.save_weather(sample_cycle.cycle_id, sample_weather)

        data = export_cycle_json(sqlite_storage, sample_cycle, [sample_route])

        assert "cycle" in data
        assert "routes" in data
        assert "captures" in data
        assert "conditions" in data
        assert "events" in data
        assert "weather" in data
        assert data["cycle"]["cycle_id"] == sample_cycle.cycle_id
        assert len(data["routes"]) == 1
        assert data["routes"][0]["route_id"] == "parleys-wolfcreek"
        assert len(data["captures"]) == 1
        assert len(data["conditions"]) == 2
        assert len(data["events"]) == 2
        assert len(data["weather"]) == 2

    def test_no_routes(self, sqlite_storage, sample_cycle):
        data = export_cycle_json(sqlite_storage, sample_cycle, routes=None)
        assert data["routes"] == []


class TestExportCycleToFile:
    def test_writes_files(self, sqlite_storage, sample_cycle, tmp_path):
        import export as export_mod

        original_dir = export_mod.OUTPUT_DIR
        export_mod.OUTPUT_DIR = tmp_path / "data"

        try:
            settings = Settings()
            settings.storage_backend = "sqlite"
            export_cycle_to_file(sqlite_storage, sample_cycle, settings=settings)

            safe_id = sample_cycle.cycle_id.replace(":", "-")
            cycle_file = tmp_path / "data" / f"cycle-{safe_id}.json"
            latest_file = tmp_path / "data" / "latest.json"

            assert cycle_file.exists()
            assert latest_file.exists()

            data = json.loads(cycle_file.read_text())
            assert data["cycle"]["cycle_id"] == sample_cycle.cycle_id
        finally:
            export_mod.OUTPUT_DIR = original_dir


class TestExportCycleIndex:
    def test_writes_index(self, sqlite_storage, sample_cycle, tmp_path):
        import export as export_mod

        original_dir = export_mod.OUTPUT_DIR
        export_mod.OUTPUT_DIR = tmp_path / "data"

        try:
            sqlite_storage.save_cycle(sample_cycle)
            settings = Settings()
            settings.storage_backend = "sqlite"
            export_cycle_index(sqlite_storage, settings=settings)

            index_file = tmp_path / "data" / "index.json"
            assert index_file.exists()

            data = json.loads(index_file.read_text())
            assert data["count"] == 1
            assert len(data["cycles"]) == 1
        finally:
            export_mod.OUTPUT_DIR = original_dir


class TestCaptureToDict:
    def test_adds_image_url(self, sqlite_storage, sample_capture):
        sqlite_storage.save_image("test.jpg", b"data")
        sample_capture.image_key = "test.jpg"
        d = _capture_to_dict(sample_capture, sqlite_storage)
        assert "image_url" in d
        assert "test.jpg" in d["image_url"]

    def test_no_image_key(self, sqlite_storage):
        capture = CaptureRecord(camera_id=1, cycle_id="test", image_key="")
        d = _capture_to_dict(capture, sqlite_storage)
        assert "image_url" not in d or d.get("image_url") is None
