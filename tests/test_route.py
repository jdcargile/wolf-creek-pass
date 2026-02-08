"""Tests for route.py -- haversine, polyline decoding, camera filtering."""

import math

from models import Camera, CameraView, Route
from route import (
    decode_route_points,
    filter_cameras_by_route,
    haversine_km,
    min_distance_to_route,
)


class TestHaversineKm:
    def test_same_point_is_zero(self):
        assert haversine_km(40.0, -111.0, 40.0, -111.0) == 0.0

    def test_slc_to_provo(self):
        # SLC (40.76, -111.89) to Provo (40.23, -111.66) ~= 61 km
        dist = haversine_km(40.76, -111.89, 40.23, -111.66)
        assert 55 < dist < 65

    def test_symmetry(self):
        d1 = haversine_km(40.0, -111.0, 41.0, -112.0)
        d2 = haversine_km(41.0, -112.0, 40.0, -111.0)
        assert abs(d1 - d2) < 0.001

    def test_known_distance(self):
        # NYC (40.7128, -74.0060) to LA (34.0522, -118.2437) ~= 3944 km
        dist = haversine_km(40.7128, -74.0060, 34.0522, -118.2437)
        assert 3900 < dist < 4000


class TestDecodeRoutePoints:
    def test_empty_polyline(self):
        route = Route(origin="A", destination="B", polyline="")
        assert decode_route_points(route) == []

    def test_decodes_known_polyline(self, sample_route):
        points = decode_route_points(sample_route)
        assert len(points) == 4
        # First point should be near (40.36, -111.14)
        assert abs(points[0][0] - 40.36) < 0.01
        assert abs(points[0][1] - (-111.14)) < 0.01


class TestMinDistanceToRoute:
    def test_empty_route(self):
        assert min_distance_to_route(40.0, -111.0, []) == float("inf")

    def test_point_on_route(self):
        route_points = [(40.0, -111.0), (40.1, -111.0)]
        dist = min_distance_to_route(40.0, -111.0, route_points)
        assert dist == 0.0

    def test_point_near_route(self):
        route_points = [(40.0, -111.0), (40.1, -111.0)]
        # Point ~0.01 degrees away (~1.1 km)
        dist = min_distance_to_route(40.0, -111.01, route_points)
        assert dist < 2.0


class TestFilterCamerasByRoute:
    def test_filters_by_proximity(self, sample_cameras, sample_route):
        matched = filter_cameras_by_route(sample_cameras, sample_route, buffer_km=5.0)
        matched_ids = {c.Id for c in matched}
        # Camera 1 and 3 are near the route, Camera 2 is far away, Camera 4 has no coords
        assert 1 in matched_ids
        assert 3 in matched_ids
        assert 2 not in matched_ids
        assert 4 not in matched_ids

    def test_empty_polyline_returns_all(self, sample_cameras):
        route = Route(origin="A", destination="B", polyline="")
        matched = filter_cameras_by_route(sample_cameras, route)
        assert len(matched) == len(sample_cameras)

    def test_sets_distance_from_route(self, sample_cameras, sample_route):
        matched = filter_cameras_by_route(sample_cameras, sample_route, buffer_km=5.0)
        for cam in matched:
            assert cam.distance_from_route_km is not None
            assert cam.distance_from_route_km >= 0

    def test_sorted_by_route_position(self, sample_route):
        # Camera A is at the start, Camera B is at the end
        import polyline as polyline_codec

        points = polyline_codec.decode(sample_route.polyline)
        cameras = [
            Camera(Id=10, Latitude=points[-1][0], Longitude=points[-1][1], Views=[]),
            Camera(Id=11, Latitude=points[0][0], Longitude=points[0][1], Views=[]),
        ]
        matched = filter_cameras_by_route(cameras, sample_route, buffer_km=5.0)
        # Camera 11 (at start of route) should come first
        assert matched[0].Id == 11
        assert matched[1].Id == 10
