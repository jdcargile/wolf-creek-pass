"""
Storage abstraction for Wolf Creek Pass.

Provides a Protocol interface with two implementations:
- SQLiteStorage: local SQLite + filesystem (for dev / offline)
- DynamoStorage: DynamoDB + S3 (for deployed + LocalStack)

Select backend via STORAGE_BACKEND env var ('sqlite' or 'dynamo').
"""

from __future__ import annotations

import json
import sqlite3
from datetime import datetime
from pathlib import Path
from typing import Protocol

import boto3
from botocore.config import Config as BotoConfig
from rich.console import Console

from models import (
    Camera,
    CaptureRecord,
    CycleSummary,
    Event,
    RoadCondition,
    Route,
    WeatherStation,
)
from settings import Settings

console = Console()


# ---- Storage Protocol ----


class Storage(Protocol):
    """Interface for all storage operations."""

    def init(self) -> None:
        """Initialize storage (create tables, buckets, etc.)."""
        ...

    # Cameras
    def save_camera(self, camera: Camera) -> None: ...
    def get_cameras(self) -> list[Camera]: ...

    # Captures
    def save_capture(self, capture: CaptureRecord) -> None: ...
    def get_recent_captures(self, limit: int = 20) -> list[CaptureRecord]: ...
    def get_captures_by_cycle(self, cycle_id: str) -> list[CaptureRecord]: ...

    # Routes
    def save_routes(self, routes: list[Route]) -> None: ...
    def get_routes(self) -> list[Route]: ...

    # Capture cycles
    def save_cycle(self, cycle: CycleSummary) -> None: ...
    def get_cycles(self, limit: int = 50) -> list[CycleSummary]: ...

    # Road conditions
    def save_road_conditions(
        self, cycle_id: str, conditions: list[RoadCondition]
    ) -> None: ...
    def get_road_conditions(self, cycle_id: str) -> list[RoadCondition]: ...

    # Events
    def save_events(self, cycle_id: str, events: list[Event]) -> None: ...
    def get_events(self, cycle_id: str) -> list[Event]: ...

    # Weather
    def save_weather(self, cycle_id: str, stations: list[WeatherStation]) -> None: ...
    def get_weather(self, cycle_id: str) -> list[WeatherStation]: ...

    # Images
    def save_image(self, key: str, data: bytes) -> str: ...
    def get_image_url(self, key: str) -> str: ...

    # Image hashes (for dedup -- skip analysis if image unchanged)
    def get_image_hash(self, camera_id: int) -> str | None: ...
    def save_image_hash(self, camera_id: int, hash_hex: str) -> None: ...


# ---- SQLite Storage ----


class SQLiteStorage:
    """Local SQLite + filesystem storage for development."""

    def __init__(self, db_path: str = "traffic_cams.db", images_dir: str = "images"):
        self.db_path = Path(db_path)
        self.images_dir = Path(images_dir)

    def _conn(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def init(self) -> None:
        self.images_dir.mkdir(exist_ok=True)
        conn = self._conn()
        c = conn.cursor()

        c.execute("""
            CREATE TABLE IF NOT EXISTS cameras (
                id INTEGER PRIMARY KEY,
                source_id TEXT,
                roadway TEXT,
                direction TEXT,
                location TEXT,
                latitude REAL,
                longitude REAL,
                distance_from_route_km REAL
            )
        """)

        c.execute("""
            CREATE TABLE IF NOT EXISTS captures (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                camera_id INTEGER,
                cycle_id TEXT,
                captured_at TEXT,
                image_key TEXT,
                has_snow INTEGER,
                has_car INTEGER,
                has_truck INTEGER,
                has_animal INTEGER,
                analysis_notes TEXT,
                roadway TEXT,
                direction TEXT,
                location TEXT,
                latitude REAL,
                longitude REAL,
                FOREIGN KEY (camera_id) REFERENCES cameras(id)
            )
        """)

        c.execute("""
            CREATE TABLE IF NOT EXISTS routes (
                route_id TEXT PRIMARY KEY,
                name TEXT,
                color TEXT,
                origin TEXT,
                destination TEXT,
                polyline TEXT,
                distance_m INTEGER,
                duration_s INTEGER,
                duration_in_traffic_s INTEGER
            )
        """)

        c.execute("""
            CREATE TABLE IF NOT EXISTS cycles (
                cycle_id TEXT PRIMARY KEY,
                started_at TEXT,
                completed_at TEXT,
                cameras_processed INTEGER,
                snow_count INTEGER,
                event_count INTEGER,
                travel_time_s INTEGER,
                distance_m INTEGER
            )
        """)

        c.execute("""
            CREATE TABLE IF NOT EXISTS road_conditions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                cycle_id TEXT,
                condition_id INTEGER,
                roadway_name TEXT,
                road_condition TEXT,
                weather_condition TEXT,
                restriction TEXT,
                encoded_polyline TEXT,
                last_updated INTEGER
            )
        """)

        c.execute("""
            CREATE TABLE IF NOT EXISTS events (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                cycle_id TEXT,
                event_id TEXT,
                event_type TEXT,
                event_sub_type TEXT,
                roadway_name TEXT,
                direction TEXT,
                description TEXT,
                severity TEXT,
                latitude REAL,
                longitude REAL,
                is_full_closure INTEGER
            )
        """)

        c.execute("""
            CREATE TABLE IF NOT EXISTS weather (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                cycle_id TEXT,
                station_id INTEGER,
                station_name TEXT,
                air_temperature TEXT,
                surface_temp TEXT,
                surface_status TEXT,
                wind_speed_avg TEXT,
                wind_speed_gust TEXT,
                wind_direction TEXT,
                precipitation TEXT,
                relative_humidity TEXT
            )
        """)

        c.execute("""
            CREATE TABLE IF NOT EXISTS image_hashes (
                camera_id INTEGER PRIMARY KEY,
                hash_hex TEXT NOT NULL
            )
        """)

        conn.commit()
        conn.close()
        console.print("[green]SQLite database initialized[/green]")

    # -- Cameras --

    def save_camera(self, camera: Camera) -> None:
        conn = self._conn()
        conn.execute(
            """INSERT OR REPLACE INTO cameras
            (id, source_id, roadway, direction, location, latitude, longitude, distance_from_route_km)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                camera.Id,
                camera.SourceId,
                camera.Roadway,
                camera.Direction,
                camera.Location,
                camera.Latitude,
                camera.Longitude,
                camera.distance_from_route_km,
            ),
        )
        conn.commit()
        conn.close()

    def get_cameras(self) -> list[Camera]:
        conn = self._conn()
        rows = conn.execute("SELECT * FROM cameras ORDER BY id").fetchall()
        conn.close()
        return [
            Camera(
                Id=r["id"],
                SourceId=r["source_id"],
                Roadway=r["roadway"],
                Direction=r["direction"],
                Location=r["location"],
                Latitude=r["latitude"],
                Longitude=r["longitude"],
                distance_from_route_km=r["distance_from_route_km"],
            )
            for r in rows
        ]

    # -- Captures --

    def save_capture(self, capture: CaptureRecord) -> None:
        conn = self._conn()
        conn.execute(
            """INSERT INTO captures
            (camera_id, cycle_id, captured_at, image_key, has_snow, has_car, has_truck, has_animal,
             analysis_notes, roadway, direction, location, latitude, longitude)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                capture.camera_id,
                capture.cycle_id,
                capture.captured_at,
                capture.image_key,
                _bool_to_int(capture.has_snow),
                _bool_to_int(capture.has_car),
                _bool_to_int(capture.has_truck),
                _bool_to_int(capture.has_animal),
                capture.analysis_notes,
                capture.roadway,
                capture.direction,
                capture.location,
                capture.latitude,
                capture.longitude,
            ),
        )
        conn.commit()
        conn.close()

    def get_recent_captures(self, limit: int = 20) -> list[CaptureRecord]:
        conn = self._conn()
        rows = conn.execute(
            "SELECT * FROM captures ORDER BY captured_at DESC LIMIT ?", (limit,)
        ).fetchall()
        conn.close()
        return [_row_to_capture(r) for r in rows]

    def get_captures_by_cycle(self, cycle_id: str) -> list[CaptureRecord]:
        conn = self._conn()
        rows = conn.execute(
            "SELECT * FROM captures WHERE cycle_id = ? ORDER BY camera_id", (cycle_id,)
        ).fetchall()
        conn.close()
        return [_row_to_capture(r) for r in rows]

    # -- Routes --

    def save_routes(self, routes: list[Route]) -> None:
        conn = self._conn()
        conn.execute("DELETE FROM routes")
        for route in routes:
            conn.execute(
                """INSERT OR REPLACE INTO routes
                (route_id, name, color, origin, destination, polyline,
                 distance_m, duration_s, duration_in_traffic_s)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (
                    route.route_id,
                    route.name,
                    route.color,
                    route.origin,
                    route.destination,
                    route.polyline,
                    route.distance_m,
                    route.duration_s,
                    route.duration_in_traffic_s,
                ),
            )
        conn.commit()
        conn.close()

    def get_routes(self) -> list[Route]:
        conn = self._conn()
        rows = conn.execute("SELECT * FROM routes ORDER BY route_id").fetchall()
        conn.close()
        return [
            Route(
                route_id=r["route_id"],
                name=r["name"] or "",
                color=r["color"] or "#3b82f6",
                origin=r["origin"] or "",
                destination=r["destination"] or "",
                polyline=r["polyline"] or "",
                distance_m=r["distance_m"] or 0,
                duration_s=r["duration_s"] or 0,
                duration_in_traffic_s=r["duration_in_traffic_s"],
            )
            for r in rows
        ]

    # -- Cycles --

    def save_cycle(self, cycle: CycleSummary) -> None:
        conn = self._conn()
        conn.execute(
            """INSERT OR REPLACE INTO cycles
            (cycle_id, started_at, completed_at, cameras_processed, snow_count, event_count,
             travel_time_s, distance_m)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                cycle.cycle_id,
                cycle.started_at,
                cycle.completed_at,
                cycle.cameras_processed,
                cycle.snow_count,
                cycle.event_count,
                cycle.travel_time_s,
                cycle.distance_m,
            ),
        )
        conn.commit()
        conn.close()

    def get_cycles(self, limit: int = 50) -> list[CycleSummary]:
        conn = self._conn()
        rows = conn.execute(
            "SELECT * FROM cycles ORDER BY started_at DESC LIMIT ?", (limit,)
        ).fetchall()
        conn.close()
        return [
            CycleSummary(
                cycle_id=r["cycle_id"],
                started_at=r["started_at"],
                completed_at=r["completed_at"] or "",
                cameras_processed=r["cameras_processed"] or 0,
                snow_count=r["snow_count"] or 0,
                event_count=r["event_count"] or 0,
                travel_time_s=r["travel_time_s"],
                distance_m=r["distance_m"],
            )
            for r in rows
        ]

    # -- Road Conditions --

    def save_road_conditions(
        self, cycle_id: str, conditions: list[RoadCondition]
    ) -> None:
        conn = self._conn()
        for c in conditions:
            conn.execute(
                """INSERT INTO road_conditions
                (cycle_id, condition_id, roadway_name, road_condition, weather_condition,
                 restriction, encoded_polyline, last_updated)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
                (
                    cycle_id,
                    c.id,
                    c.roadway_name,
                    c.road_condition,
                    c.weather_condition,
                    c.restriction,
                    c.encoded_polyline,
                    c.last_updated,
                ),
            )
        conn.commit()
        conn.close()

    def get_road_conditions(self, cycle_id: str) -> list[RoadCondition]:
        conn = self._conn()
        rows = conn.execute(
            "SELECT * FROM road_conditions WHERE cycle_id = ?", (cycle_id,)
        ).fetchall()
        conn.close()
        return [
            RoadCondition(
                id=r["condition_id"],
                roadway_name=r["roadway_name"],
                road_condition=r["road_condition"],
                weather_condition=r["weather_condition"],
                restriction=r["restriction"],
                encoded_polyline=r["encoded_polyline"],
                last_updated=r["last_updated"],
            )
            for r in rows
        ]

    # -- Events --

    def save_events(self, cycle_id: str, events: list[Event]) -> None:
        conn = self._conn()
        for e in events:
            conn.execute(
                """INSERT INTO events
                (cycle_id, event_id, event_type, event_sub_type, roadway_name, direction,
                 description, severity, latitude, longitude, is_full_closure)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (
                    cycle_id,
                    e.id,
                    e.event_type,
                    e.event_sub_type,
                    e.roadway_name,
                    e.direction,
                    e.description,
                    e.severity,
                    e.latitude,
                    e.longitude,
                    1 if e.is_full_closure else 0,
                ),
            )
        conn.commit()
        conn.close()

    def get_events(self, cycle_id: str) -> list[Event]:
        conn = self._conn()
        rows = conn.execute(
            "SELECT * FROM events WHERE cycle_id = ?", (cycle_id,)
        ).fetchall()
        conn.close()
        return [
            Event(
                id=r["event_id"],
                event_type=r["event_type"],
                event_sub_type=r["event_sub_type"],
                roadway_name=r["roadway_name"],
                direction=r["direction"],
                description=r["description"],
                severity=r["severity"],
                latitude=r["latitude"],
                longitude=r["longitude"],
                is_full_closure=bool(r["is_full_closure"]),
            )
            for r in rows
        ]

    # -- Weather --

    def save_weather(self, cycle_id: str, stations: list[WeatherStation]) -> None:
        conn = self._conn()
        for w in stations:
            conn.execute(
                """INSERT INTO weather
                (cycle_id, station_id, station_name, air_temperature, surface_temp,
                 surface_status, wind_speed_avg, wind_speed_gust, wind_direction,
                 precipitation, relative_humidity)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (
                    cycle_id,
                    w.id,
                    w.station_name,
                    w.air_temperature,
                    w.surface_temp,
                    w.surface_status,
                    w.wind_speed_avg,
                    w.wind_speed_gust,
                    w.wind_direction,
                    w.precipitation,
                    w.relative_humidity,
                ),
            )
        conn.commit()
        conn.close()

    def get_weather(self, cycle_id: str) -> list[WeatherStation]:
        conn = self._conn()
        rows = conn.execute(
            "SELECT * FROM weather WHERE cycle_id = ?", (cycle_id,)
        ).fetchall()
        conn.close()
        return [
            WeatherStation(
                id=r["station_id"],
                station_name=r["station_name"],
                air_temperature=r["air_temperature"],
                surface_temp=r["surface_temp"],
                surface_status=r["surface_status"],
                wind_speed_avg=r["wind_speed_avg"],
                wind_speed_gust=r["wind_speed_gust"],
                wind_direction=r["wind_direction"],
                precipitation=r["precipitation"],
                relative_humidity=r["relative_humidity"],
            )
            for r in rows
        ]

    # -- Images --

    def save_image(self, key: str, data: bytes) -> str:
        path = self.images_dir / key
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(data)
        return str(path)

    def get_image_url(self, key: str) -> str:
        return str(self.images_dir / key)

    # -- Image Hashes --

    def get_image_hash(self, camera_id: int) -> str | None:
        conn = self._conn()
        row = conn.execute(
            "SELECT hash_hex FROM image_hashes WHERE camera_id = ?", (camera_id,)
        ).fetchone()
        conn.close()
        return row["hash_hex"] if row else None

    def save_image_hash(self, camera_id: int, hash_hex: str) -> None:
        conn = self._conn()
        conn.execute(
            "INSERT OR REPLACE INTO image_hashes (camera_id, hash_hex) VALUES (?, ?)",
            (camera_id, hash_hex),
        )
        conn.commit()
        conn.close()


# ---- DynamoDB + S3 Storage ----


class DynamoStorage:
    """AWS DynamoDB + S3 storage for deployed and LocalStack environments."""

    def __init__(self, settings: Settings):
        self.table_name = settings.table_name
        self.bucket_name = settings.bucket_name

        boto_kwargs: dict = {"region_name": settings.aws_default_region}
        if settings.aws_endpoint_url:
            boto_kwargs["endpoint_url"] = settings.aws_endpoint_url
            boto_kwargs["config"] = BotoConfig(signature_version="s3v4")

        self.dynamodb = boto3.resource("dynamodb", **boto_kwargs)
        self.s3 = boto3.client("s3", **boto_kwargs)
        self.table = self.dynamodb.Table(self.table_name)
        self._endpoint_url = settings.aws_endpoint_url

    def init(self) -> None:
        """For DynamoDB, tables are created via CDK. This is a no-op in production.
        For LocalStack, we create the table and bucket if they don't exist."""
        if self._endpoint_url:
            self._init_localstack()
        console.print("[green]DynamoDB storage ready[/green]")

    def _init_localstack(self) -> None:
        """Create table and bucket in LocalStack if they don't exist."""
        client = self.dynamodb.meta.client
        try:
            client.describe_table(TableName=self.table_name)
        except client.exceptions.ResourceNotFoundException:
            client.create_table(
                TableName=self.table_name,
                KeySchema=[
                    {"AttributeName": "PK", "KeyType": "HASH"},
                    {"AttributeName": "SK", "KeyType": "RANGE"},
                ],
                AttributeDefinitions=[
                    {"AttributeName": "PK", "AttributeType": "S"},
                    {"AttributeName": "SK", "AttributeType": "S"},
                    {"AttributeName": "GSI1PK", "AttributeType": "S"},
                    {"AttributeName": "GSI1SK", "AttributeType": "S"},
                ],
                GlobalSecondaryIndexes=[
                    {
                        "IndexName": "GSI1",
                        "KeySchema": [
                            {"AttributeName": "GSI1PK", "KeyType": "HASH"},
                            {"AttributeName": "GSI1SK", "KeyType": "RANGE"},
                        ],
                        "Projection": {"ProjectionType": "ALL"},
                    }
                ],
                BillingMode="PAY_PER_REQUEST",
            )
            console.print(f"[green]Created LocalStack table: {self.table_name}[/green]")

        try:
            self.s3.head_bucket(Bucket=self.bucket_name)
        except Exception:
            self.s3.create_bucket(
                Bucket=self.bucket_name,
                CreateBucketConfiguration={"LocationConstraint": "us-west-2"},
            )
            console.print(
                f"[green]Created LocalStack bucket: {self.bucket_name}[/green]"
            )

    # -- Cameras --

    def save_camera(self, camera: Camera) -> None:
        self.table.put_item(
            Item=_strip_none(
                {
                    "PK": f"CAMERA#{camera.Id}",
                    "SK": "META",
                    "GSI1PK": "CAMERA",
                    "GSI1SK": str(camera.Id),
                    "source_id": camera.SourceId,
                    "roadway": camera.Roadway,
                    "direction": camera.Direction,
                    "location": camera.Location,
                    "latitude": _decimal_safe(camera.Latitude),
                    "longitude": _decimal_safe(camera.Longitude),
                    "distance_from_route_km": _decimal_safe(
                        camera.distance_from_route_km
                    ),
                }
            )
        )

    def get_cameras(self) -> list[Camera]:
        resp = self.table.query(
            IndexName="GSI1",
            KeyConditionExpression="GSI1PK = :pk",
            ExpressionAttributeValues={":pk": "CAMERA"},
        )
        return [
            Camera(
                Id=int(item["GSI1SK"]),
                SourceId=item.get("source_id"),
                Roadway=item.get("roadway"),
                Direction=item.get("direction"),
                Location=item.get("location"),
                Latitude=_float_safe(item.get("latitude")),
                Longitude=_float_safe(item.get("longitude")),
                distance_from_route_km=_float_safe(item.get("distance_from_route_km")),
            )
            for item in resp.get("Items", [])
        ]

    # -- Captures --

    def save_capture(self, capture: CaptureRecord) -> None:
        self.table.put_item(
            Item=_strip_none(
                {
                    "PK": f"CAMERA#{capture.camera_id}",
                    "SK": f"CAPTURE#{capture.captured_at}",
                    "GSI1PK": f"CYCLE#{capture.cycle_id}",
                    "GSI1SK": f"CAMERA#{capture.camera_id}",
                    "cycle_id": capture.cycle_id,
                    "captured_at": capture.captured_at,
                    "image_key": capture.image_key,
                    "has_snow": capture.has_snow,
                    "has_car": capture.has_car,
                    "has_truck": capture.has_truck,
                    "has_animal": capture.has_animal,
                    "analysis_notes": capture.analysis_notes,
                    "roadway": capture.roadway,
                    "direction": capture.direction,
                    "location": capture.location,
                    "latitude": _decimal_safe(capture.latitude),
                    "longitude": _decimal_safe(capture.longitude),
                }
            )
        )

    def get_recent_captures(self, limit: int = 20) -> list[CaptureRecord]:
        # Get latest cycle, then get captures from it
        cycles = self.get_cycles(limit=1)
        if not cycles:
            return []
        return self.get_captures_by_cycle(cycles[0].cycle_id)[:limit]

    def get_captures_by_cycle(self, cycle_id: str) -> list[CaptureRecord]:
        resp = self.table.query(
            IndexName="GSI1",
            KeyConditionExpression="GSI1PK = :pk AND begins_with(GSI1SK, :sk_prefix)",
            ExpressionAttributeValues={
                ":pk": f"CYCLE#{cycle_id}",
                ":sk_prefix": "CAMERA#",
            },
        )
        return [
            CaptureRecord(
                camera_id=int(item["GSI1SK"].split("#")[1]),
                cycle_id=item.get("cycle_id", cycle_id),
                captured_at=item.get("captured_at", ""),
                image_key=item.get("image_key", ""),
                has_snow=item.get("has_snow"),
                has_car=item.get("has_car"),
                has_truck=item.get("has_truck"),
                has_animal=item.get("has_animal"),
                analysis_notes=item.get("analysis_notes", ""),
                roadway=item.get("roadway"),
                direction=item.get("direction"),
                location=item.get("location"),
                latitude=_float_safe(item.get("latitude")),
                longitude=_float_safe(item.get("longitude")),
            )
            for item in resp.get("Items", [])
        ]

    # -- Routes --

    def save_routes(self, routes: list[Route]) -> None:
        for route in routes:
            self.table.put_item(
                Item=_strip_none(
                    {
                        "PK": f"ROUTE#{route.route_id}",
                        "SK": "META",
                        "GSI1PK": "ROUTE",
                        "GSI1SK": route.route_id,
                        "route_id": route.route_id,
                        "name": route.name,
                        "color": route.color,
                        "origin": route.origin,
                        "destination": route.destination,
                        "polyline": route.polyline,
                        "distance_m": route.distance_m,
                        "duration_s": route.duration_s,
                        "duration_in_traffic_s": route.duration_in_traffic_s,
                    }
                )
            )

    def get_routes(self) -> list[Route]:
        resp = self.table.query(
            IndexName="GSI1",
            KeyConditionExpression="GSI1PK = :pk",
            ExpressionAttributeValues={":pk": "ROUTE"},
        )
        return [
            Route(
                route_id=item.get("route_id", ""),
                name=item.get("name", ""),
                color=item.get("color", "#3b82f6"),
                origin=item.get("origin", ""),
                destination=item.get("destination", ""),
                polyline=item.get("polyline", ""),
                distance_m=int(item.get("distance_m", 0)),
                duration_s=int(item.get("duration_s", 0)),
                duration_in_traffic_s=_int_safe(item.get("duration_in_traffic_s")),
            )
            for item in resp.get("Items", [])
        ]

    # -- Cycles --

    def save_cycle(self, cycle: CycleSummary) -> None:
        self.table.put_item(
            Item=_strip_none(
                {
                    "PK": "CYCLES",
                    "SK": f"CYCLE#{cycle.cycle_id}",
                    "GSI1PK": f"CYCLE#{cycle.cycle_id}",
                    "GSI1SK": "META",
                    "cycle_id": cycle.cycle_id,
                    "started_at": cycle.started_at,
                    "completed_at": cycle.completed_at,
                    "cameras_processed": cycle.cameras_processed,
                    "snow_count": cycle.snow_count,
                    "event_count": cycle.event_count,
                    "travel_time_s": cycle.travel_time_s,
                    "distance_m": cycle.distance_m,
                }
            )
        )

    def get_cycles(self, limit: int = 50) -> list[CycleSummary]:
        resp = self.table.query(
            KeyConditionExpression="PK = :pk AND begins_with(SK, :sk_prefix)",
            ExpressionAttributeValues={
                ":pk": "CYCLES",
                ":sk_prefix": "CYCLE#",
            },
            ScanIndexForward=False,
            Limit=limit,
        )
        return [
            CycleSummary(
                cycle_id=item.get("cycle_id", ""),
                started_at=item.get("started_at", ""),
                completed_at=item.get("completed_at", ""),
                cameras_processed=int(item.get("cameras_processed", 0)),
                snow_count=int(item.get("snow_count", 0)),
                event_count=int(item.get("event_count", 0)),
                travel_time_s=_int_safe(item.get("travel_time_s")),
                distance_m=_int_safe(item.get("distance_m")),
            )
            for item in resp.get("Items", [])
        ]

    # -- Road Conditions --

    def save_road_conditions(
        self, cycle_id: str, conditions: list[RoadCondition]
    ) -> None:
        for c in conditions:
            self.table.put_item(
                Item=_strip_none(
                    {
                        "PK": f"CONDITION#{c.roadway_name}",
                        "SK": cycle_id,
                        "GSI1PK": f"CYCLE#{cycle_id}",
                        "GSI1SK": f"CONDITION#{c.roadway_name}",
                        "condition_id": c.id,
                        "roadway_name": c.roadway_name,
                        "road_condition": c.road_condition,
                        "weather_condition": c.weather_condition,
                        "restriction": c.restriction,
                        "encoded_polyline": c.encoded_polyline,
                        "last_updated": c.last_updated,
                    }
                )
            )

    def get_road_conditions(self, cycle_id: str) -> list[RoadCondition]:
        resp = self.table.query(
            IndexName="GSI1",
            KeyConditionExpression="GSI1PK = :pk AND begins_with(GSI1SK, :prefix)",
            ExpressionAttributeValues={
                ":pk": f"CYCLE#{cycle_id}",
                ":prefix": "CONDITION#",
            },
        )
        return [
            RoadCondition(
                id=int(item.get("condition_id", 0)),
                roadway_name=item.get("roadway_name", ""),
                road_condition=item.get("road_condition", ""),
                weather_condition=item.get("weather_condition", ""),
                restriction=item.get("restriction", ""),
                encoded_polyline=item.get("encoded_polyline", ""),
                last_updated=int(item.get("last_updated", 0)),
            )
            for item in resp.get("Items", [])
        ]

    # -- Events --

    def save_events(self, cycle_id: str, events: list[Event]) -> None:
        for e in events:
            self.table.put_item(
                Item=_strip_none(
                    {
                        "PK": f"EVENT#{e.id}",
                        "SK": "META",
                        "GSI1PK": f"CYCLE#{cycle_id}",
                        "GSI1SK": f"EVENT#{e.id}",
                        "event_id": e.id,
                        "event_type": e.event_type,
                        "event_sub_type": e.event_sub_type,
                        "roadway_name": e.roadway_name,
                        "direction": e.direction,
                        "description": e.description,
                        "severity": e.severity,
                        "latitude": _decimal_safe(e.latitude),
                        "longitude": _decimal_safe(e.longitude),
                        "is_full_closure": e.is_full_closure,
                    }
                )
            )

    def get_events(self, cycle_id: str) -> list[Event]:
        resp = self.table.query(
            IndexName="GSI1",
            KeyConditionExpression="GSI1PK = :pk AND begins_with(GSI1SK, :prefix)",
            ExpressionAttributeValues={
                ":pk": f"CYCLE#{cycle_id}",
                ":prefix": "EVENT#",
            },
        )
        return [
            Event(
                id=item.get("event_id", ""),
                event_type=item.get("event_type", ""),
                event_sub_type=item.get("event_sub_type", ""),
                roadway_name=item.get("roadway_name", ""),
                direction=item.get("direction", ""),
                description=item.get("description", ""),
                severity=item.get("severity", ""),
                latitude=_float_safe(item.get("latitude")),
                longitude=_float_safe(item.get("longitude")),
                is_full_closure=bool(item.get("is_full_closure", False)),
            )
            for item in resp.get("Items", [])
        ]

    # -- Weather --

    def save_weather(self, cycle_id: str, stations: list[WeatherStation]) -> None:
        for w in stations:
            self.table.put_item(
                Item=_strip_none(
                    {
                        "PK": f"WEATHER#{w.station_name}",
                        "SK": cycle_id,
                        "GSI1PK": f"CYCLE#{cycle_id}",
                        "GSI1SK": f"WEATHER#{w.station_name}",
                        "station_id": w.id,
                        "station_name": w.station_name,
                        "air_temperature": w.air_temperature,
                        "surface_temp": w.surface_temp,
                        "surface_status": w.surface_status,
                        "wind_speed_avg": w.wind_speed_avg,
                        "wind_speed_gust": w.wind_speed_gust,
                        "wind_direction": w.wind_direction,
                        "precipitation": w.precipitation,
                        "relative_humidity": w.relative_humidity,
                    }
                )
            )

    def get_weather(self, cycle_id: str) -> list[WeatherStation]:
        resp = self.table.query(
            IndexName="GSI1",
            KeyConditionExpression="GSI1PK = :pk AND begins_with(GSI1SK, :prefix)",
            ExpressionAttributeValues={
                ":pk": f"CYCLE#{cycle_id}",
                ":prefix": "WEATHER#",
            },
        )
        return [
            WeatherStation(
                id=int(item.get("station_id", 0)),
                station_name=item.get("station_name", ""),
                air_temperature=item.get("air_temperature", ""),
                surface_temp=item.get("surface_temp", ""),
                surface_status=item.get("surface_status", ""),
                wind_speed_avg=item.get("wind_speed_avg", ""),
                wind_speed_gust=item.get("wind_speed_gust", ""),
                wind_direction=item.get("wind_direction", ""),
                precipitation=item.get("precipitation", ""),
                relative_humidity=item.get("relative_humidity", ""),
            )
            for item in resp.get("Items", [])
        ]

    # -- Images --

    def save_image(self, key: str, data: bytes) -> str:
        self.s3.put_object(Bucket=self.bucket_name, Key=f"images/{key}", Body=data)
        return f"images/{key}"

    def get_image_url(self, key: str) -> str:
        if self._endpoint_url:
            return f"{self._endpoint_url}/{self.bucket_name}/images/{key}"
        return f"https://{self.bucket_name}.s3.amazonaws.com/images/{key}"

    # -- Image Hashes --

    def get_image_hash(self, camera_id: int) -> str | None:
        resp = self.table.get_item(Key={"PK": f"HASH#{camera_id}", "SK": "HASH"})
        item = resp.get("Item")
        return item["hash_hex"] if item else None

    def save_image_hash(self, camera_id: int, hash_hex: str) -> None:
        self.table.put_item(
            Item={
                "PK": f"HASH#{camera_id}",
                "SK": "HASH",
                "hash_hex": hash_hex,
            }
        )


# ---- Factory ----


def create_storage(settings: Settings) -> Storage:
    """Create a storage backend based on settings."""
    if settings.storage_backend == "dynamo":
        return DynamoStorage(settings)  # type: ignore[return-value]
    return SQLiteStorage()  # type: ignore[return-value]


# ---- Helpers ----


def _bool_to_int(val: bool | None) -> int | None:
    if val is None:
        return None
    return 1 if val else 0


def _row_to_capture(r: sqlite3.Row) -> CaptureRecord:
    return CaptureRecord(
        camera_id=r["camera_id"],
        cycle_id=r["cycle_id"] or "",
        captured_at=r["captured_at"] or "",
        image_key=r["image_key"] or "",
        has_snow=_int_to_bool(r["has_snow"]),
        has_car=_int_to_bool(r["has_car"]),
        has_truck=_int_to_bool(r["has_truck"]),
        has_animal=_int_to_bool(r["has_animal"]),
        analysis_notes=r["analysis_notes"] or "",
        roadway=r["roadway"],
        direction=r["direction"],
        location=r["location"],
        latitude=r["latitude"],
        longitude=r["longitude"],
    )


def _int_to_bool(val: int | None) -> bool | None:
    if val is None:
        return None
    return bool(val)


def _strip_none(d: dict) -> dict:
    """Remove None values from a dict (DynamoDB doesn't accept None)."""
    return {k: v for k, v in d.items() if v is not None}


def _decimal_safe(val: float | None):
    """Convert float to Decimal-safe string for DynamoDB."""
    if val is None:
        return None
    return str(val)


def _float_safe(val) -> float | None:
    """Convert DynamoDB Decimal/string back to float."""
    if val is None:
        return None
    return float(val)


def _int_safe(val) -> int | None:
    """Convert DynamoDB Decimal/string back to int."""
    if val is None:
        return None
    return int(val)
