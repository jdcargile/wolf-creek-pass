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
    fetch_route_passes,
    fetch_all_snow_plows,
    fetch_route_plows,
    is_wolf_creek_closed,
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
        stations = fetch_route_weather(FAKE_KEY, ["Wolf Creek Pass", "Daniels Summit"])
        names = [s.station_name for s in stations]
        assert "Wolf Creek Pass" in names
        assert "Daniels Summit" in names
        assert "Wendover I-80" not in names


class TestFetchRoutePasses:
    @responses.activate
    def test_filters_by_id(self):
        responses.add(
            responses.GET,
            f"{BASE_URL}/mountainpasses",
            json=[
                {
                    "Id": 44,
                    "Name": "SR-35 Wolf Creek Pass",
                    "Roadway": "SR-35",
                    "MaxElevation": "9488",
                    "Latitude": 40.48,
                    "Longitude": -111.03,
                    "StationName": "SR-35 @ Wolf Creek",
                    "AirTemperature": "25",
                    "WindSpeed": "15",
                    "WindGust": "30",
                    "WindDirection": "NW",
                    "SurfaceTemp": "22",
                    "SurfaceStatus": "Snow/Ice",
                    "Visibility": "0.5",
                    "Forecasts": "Evening;Snow expected",
                    "SeasonalInfo": [
                        {
                            "SeasonalClosureStatus": "OPEN",
                            "SeasonalClosureDescription": "Francis to Hanna",
                        }
                    ],
                    "SeasonalRouteName": "Route 35",
                    "SeasonalClosureTitle": "SR 35 Wolf Creek Pass",
                },
                {
                    "Id": 9,
                    "Name": "I-80 Parleys Summit",
                    "Roadway": "I-80",
                    "AirTemperature": "32",
                    "SeasonalInfo": [],
                },
                {
                    "Id": 99,
                    "Name": "Cedar Breaks Summit",
                    "Roadway": "SR-14",
                    "AirTemperature": "20",
                },
            ],
            status=200,
        )
        passes = fetch_route_passes(FAKE_KEY, [44, 9])
        names = [p.name for p in passes]
        assert "SR-35 Wolf Creek Pass" in names
        assert "I-80 Parleys Summit" in names
        assert "Cedar Breaks Summit" not in names

    @responses.activate
    def test_parses_all_fields(self):
        responses.add(
            responses.GET,
            f"{BASE_URL}/mountainpasses",
            json=[
                {
                    "Id": 44,
                    "Name": "SR-35 Wolf Creek Pass",
                    "Roadway": "SR-35",
                    "MaxElevation": "9488",
                    "Latitude": 40.48,
                    "Longitude": -111.03,
                    "StationName": "SR-35 @ Wolf Creek",
                    "AirTemperature": "28",
                    "WindSpeed": "5",
                    "WindGust": "7",
                    "WindDirection": "NE",
                    "SurfaceTemp": "",
                    "SurfaceStatus": "",
                    "Visibility": "",
                    "Forecasts": "",
                    "SeasonalInfo": [
                        {
                            "SeasonalClosureStatus": "CLOSED",
                            "SeasonalClosureDescription": "Seasonal closure",
                        }
                    ],
                    "SeasonalRouteName": "Route 35",
                    "SeasonalClosureTitle": "SR 35 Wolf Creek Pass",
                },
            ],
            status=200,
        )
        passes = fetch_route_passes(FAKE_KEY, [44])
        assert len(passes) == 1
        p = passes[0]
        assert p.closure_status == "CLOSED"
        assert p.closure_description == "Seasonal closure"
        assert p.station_name == "SR-35 @ Wolf Creek"
        assert p.seasonal_route_name == "Route 35"
        assert p.seasonal_closure_title == "SR 35 Wolf Creek Pass"
        assert p.wind_speed == "5"
        assert p.wind_gust == "7"


class TestIsWolfCreekClosed:
    @responses.activate
    def test_open(self):
        responses.add(
            responses.GET,
            f"{BASE_URL}/mountainpasses",
            json=[
                {
                    "Id": 44,
                    "Name": "Wolf Creek Pass",
                    "SeasonalInfo": [{"SeasonalClosureStatus": "OPEN"}],
                },
            ],
            status=200,
        )
        assert is_wolf_creek_closed(FAKE_KEY) is False

    @responses.activate
    def test_closed(self):
        responses.add(
            responses.GET,
            f"{BASE_URL}/mountainpasses",
            json=[
                {
                    "Id": 44,
                    "Name": "Wolf Creek Pass",
                    "SeasonalInfo": [{"SeasonalClosureStatus": "CLOSED"}],
                },
            ],
            status=200,
        )
        assert is_wolf_creek_closed(FAKE_KEY) is True

    @responses.activate
    def test_not_found(self):
        responses.add(
            responses.GET,
            f"{BASE_URL}/mountainpasses",
            json=[{"Id": 10, "Name": "Parley's Summit"}],
            status=200,
        )
        assert is_wolf_creek_closed(FAKE_KEY) is False


class TestFetchAllSnowPlows:
    @responses.activate
    def test_parses_plows(self):
        responses.add(
            responses.GET,
            f"{BASE_URL}/servicevehicles",
            json=[
                {
                    "Id": 501,
                    "Name": "Plow Unit 42",
                    "Latitude": 40.37,
                    "Longitude": -111.12,
                    "Heading": 180.0,
                    "Speed": 25.0,
                    "LastUpdated": "2026-02-07T12:30:00",
                },
            ],
            status=200,
        )
        plows = fetch_all_snow_plows(FAKE_KEY)
        assert len(plows) == 1
        assert plows[0].id == 501
        assert plows[0].name == "Plow Unit 42"
        assert plows[0].speed == 25.0

    @responses.activate
    def test_empty_response(self):
        responses.add(
            responses.GET,
            f"{BASE_URL}/servicevehicles",
            json=[],
            status=200,
        )
        assert fetch_all_snow_plows(FAKE_KEY) == []


class TestFetchRoutePlows:
    @responses.activate
    def test_filters_by_proximity(self, sample_route):
        responses.add(
            responses.GET,
            f"{BASE_URL}/servicevehicles",
            json=[
                {
                    "Id": 501,
                    "Name": "Near Route Plow",
                    "Latitude": 40.37,
                    "Longitude": -111.12,
                    "Speed": 25.0,
                },
                {
                    "Id": 502,
                    "Name": "Far Away Plow",
                    "Latitude": 38.0,
                    "Longitude": -109.0,
                    "Speed": 30.0,
                },
            ],
            status=200,
        )
        plows = fetch_route_plows(FAKE_KEY, [sample_route], buffer_km=5.0)
        assert len(plows) == 1
        assert plows[0].name == "Near Route Plow"

    @responses.activate
    def test_empty_when_no_plows(self, sample_route):
        responses.add(
            responses.GET,
            f"{BASE_URL}/servicevehicles",
            json=[],
            status=200,
        )
        assert fetch_route_plows(FAKE_KEY, [sample_route]) == []
