"""Tests for udot.py -- UDOT API client and route filtering."""

from unittest.mock import patch

import responses

from models import Route
from udot import (
    _fetch,
    fetch_all_cameras,
    fetch_route_conditions,
    fetch_route_events,
    fetch_route_weather,
    fetch_mountain_pass_info,
    BASE_URL,
)


FAKE_KEY = "test-api-key"


class TestFetch:
    @responses.activate
    def test_returns_list(self):
        responses.add(
            responses.GET,
            f"{BASE_URL}/cameras",
            json=[{"Id": 1}, {"Id": 2}],
            status=200,
        )
        result = _fetch("cameras", FAKE_KEY)
        assert len(result) == 2

    @responses.activate
    def test_non_list_returns_empty(self):
        responses.add(
            responses.GET,
            f"{BASE_URL}/cameras",
            json={"error": "something"},
            status=200,
        )
        result = _fetch("cameras", FAKE_KEY)
        assert result == []

    @responses.activate
    def test_http_error_returns_empty(self):
        responses.add(
            responses.GET,
            f"{BASE_URL}/cameras",
            json={"error": "not found"},
            status=500,
        )
        result = _fetch("cameras", FAKE_KEY)
        assert result == []


class TestFetchAllCameras:
    @responses.activate
    def test_parses_cameras(self):
        responses.add(
            responses.GET,
            f"{BASE_URL}/cameras",
            json=[
                {
                    "Id": 42,
                    "Roadway": "SR-35",
                    "Direction": "NB",
                    "Location": "Wolf Creek",
                    "Latitude": 40.37,
                    "Longitude": -111.12,
                    "Views": [{"Url": "http://cam.com/42.jpg"}],
                }
            ],
            status=200,
        )
        cameras = fetch_all_cameras(FAKE_KEY)
        assert len(cameras) == 1
        assert cameras[0].Id == 42
        assert cameras[0].Roadway == "SR-35"
        assert len(cameras[0].Views) == 1


class TestFetchRouteConditions:
    @responses.activate
    def test_filters_by_roadway_name(self):
        responses.add(
            responses.GET,
            f"{BASE_URL}/roadconditions",
            json=[
                {
                    "Id": 1,
                    "RoadwayName": "SR-35 Wolf Creek Pass",
                    "RoadCondition": "Snow",
                    "WeatherCondition": "",
                },
                {
                    "Id": 2,
                    "RoadwayName": "I-80 Wendover",
                    "RoadCondition": "Dry",
                    "WeatherCondition": "",
                },
                {
                    "Id": 3,
                    "RoadwayName": "US-40 Heber",
                    "RoadCondition": "Wet",
                    "WeatherCondition": "",
                },
            ],
            status=200,
        )
        route = Route(origin="A", destination="B")
        conditions = fetch_route_conditions(FAKE_KEY, route)
        names = [c.roadway_name for c in conditions]
        assert "SR-35 Wolf Creek Pass" in names
        assert "US-40 Heber" in names
        assert "I-80 Wendover" not in names


class TestFetchRouteEvents:
    @responses.activate
    def test_filters_by_proximity(self, sample_route):
        responses.add(
            responses.GET,
            f"{BASE_URL}/event",
            json=[
                {
                    "ID": "1",
                    "EventType": "construction",
                    "Latitude": 40.37,
                    "Longitude": -111.12,
                    "Description": "Near route",
                    "RoadwayName": "SR-35",
                },
                {
                    "ID": "2",
                    "EventType": "accident",
                    "Latitude": 38.0,
                    "Longitude": -109.0,
                    "Description": "Far away",
                    "RoadwayName": "I-70",
                },
            ],
            status=200,
        )
        events = fetch_route_events(FAKE_KEY, sample_route, buffer_km=5.0)
        assert len(events) == 1
        assert events[0].id == "1"


class TestFetchRouteWeather:
    @responses.activate
    def test_filters_by_station_name(self):
        responses.add(
            responses.GET,
            f"{BASE_URL}/weatherstations",
            json=[
                {"Id": 1, "StationName": "Wolf Creek Pass", "AirTemperature": "28"},
                {"Id": 2, "StationName": "Wendover I-80", "AirTemperature": "45"},
                {"Id": 3, "StationName": "Daniels Summit", "AirTemperature": "30"},
            ],
            status=200,
        )
        route = Route(origin="A", destination="B")
        stations = fetch_route_weather(FAKE_KEY, route)
        names = [s.station_name for s in stations]
        assert "Wolf Creek Pass" in names
        assert "Daniels Summit" in names
        assert "Wendover I-80" not in names


class TestFetchMountainPassInfo:
    @responses.activate
    def test_finds_wolf_creek(self):
        responses.add(
            responses.GET,
            f"{BASE_URL}/mountainpasses",
            json=[
                {"Name": "Parley's Summit", "AirTemp": "35"},
                {"Name": "Wolf Creek Pass", "AirTemp": "25"},
            ],
            status=200,
        )
        result = fetch_mountain_pass_info(FAKE_KEY)
        assert result is not None
        assert result["Name"] == "Wolf Creek Pass"

    @responses.activate
    def test_not_found(self):
        responses.add(
            responses.GET,
            f"{BASE_URL}/mountainpasses",
            json=[{"Name": "Parley's Summit"}],
            status=200,
        )
        assert fetch_mountain_pass_info(FAKE_KEY) is None
