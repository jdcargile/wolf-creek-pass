"""Application settings loaded from environment / .env file."""

from __future__ import annotations

from dataclasses import dataclass, field

from pydantic import Field as PydanticField
from pydantic_settings import BaseSettings


# ---------------------------------------------------------------------------
# Route definitions -- named routes from Riverton to Hanna
# ---------------------------------------------------------------------------
# Waypoints use coordinates on SR-35 (Wolf Creek Pass cameras) to force
# Google Directions through the correct mountain pass rather than letting
# it wander onto forest roads or other highways.
# ---------------------------------------------------------------------------


@dataclass
class RouteConfig:
    """Static definition of a named route with UDOT 511 share ID."""

    route_id: str
    name: str
    share_id: str = ""  # UDOT 511 shared route UUID
    camera_ids: list[int] = field(default_factory=list)
    pass_ids: list[int] = field(default_factory=list)
    weather_station_names: list[str] = field(default_factory=list)
    color: str = "#3b82f6"  # Hex color for map polyline


ROUTES: list[RouteConfig] = [
    # ── PRIMARY: Parley's Canyon → SR-35 Wolf Creek Pass ──────────────
    # I-15 N → I-215 E → I-80 E (Parley's Canyon) → US-40 E → exit 4
    # → UT-248 to Kamas → UT-32 S to Francis → UT-35 E over Wolf Creek
    # Pass → North Fork Rd to Hanna.
    # ~88.8 mi, ~1h 45m per UDOT 511 routing.
    #
    # share_id is from https://prod-ut.ibi511.com/map#route-{share_id}
    RouteConfig(
        route_id="parleys-wolfcreek",
        name="Parley's / Wolf Creek",
        share_id="720cd440-85f0-433e-8eba-8e505869abd4",
        color="#3b82f6",  # blue
        camera_ids=[
            90602,  # SR-248 RWIS EB @ MP 8.95 (Kamas corridor)
            90912,  # I-80 EB @ Parley's Summit / MP 139.24
            90544,  # SR-35 RWIS @ Wolf Creek / MP 9.92
            90779,  # SR-35 RWIS EB @ Wolf Creek Pass / MP 19.33
            90817,  # SR-208 @ MP 7.68 (Duchesne area)
        ],
        pass_ids=[
            9,  # I-80 Parley's Summit (7016')
            75,  # SR-248 Summit (7000')
            44,  # SR-35 Wolf Creek Pass (9488')
        ],
        weather_station_names=[
            "I-80 @ Parleys Summit",
            "SR-35 @ Wolf Creek",
            "SR-35 @ Wolf Creek Pass",
        ],
    ),
]


def get_all_camera_ids() -> list[int]:
    """Union of all camera IDs across all routes, deduplicated, order preserved."""
    seen: set[int] = set()
    result: list[int] = []
    for route_cfg in ROUTES:
        for cid in route_cfg.camera_ids:
            if cid not in seen:
                seen.add(cid)
                result.append(cid)
    return result


def get_all_pass_ids() -> list[int]:
    """Union of all pass IDs across all routes, deduplicated, order preserved."""
    seen: set[int] = set()
    result: list[int] = []
    for route_cfg in ROUTES:
        for pid in route_cfg.pass_ids:
            if pid not in seen:
                seen.add(pid)
                result.append(pid)
    return result


def get_all_weather_station_names() -> list[str]:
    """Union of all weather station names across all routes, deduplicated, order preserved."""
    seen: set[str] = set()
    result: list[str] = []
    for route_cfg in ROUTES:
        for name in route_cfg.weather_station_names:
            lower = name.lower()
            if lower not in seen:
                seen.add(lower)
                result.append(name)
    return result


def get_route_ids_for_camera(camera_id: int) -> list[str]:
    """Return which route IDs a camera belongs to."""
    return [r.route_id for r in ROUTES if camera_id in r.camera_ids]


class Settings(BaseSettings):
    """All configuration for Wolf Creek Pass, loaded from .env or environment."""

    # API keys
    udot_api_key: str = PydanticField(description="UDOT Traffic API key")

    # Storage backend
    storage_backend: str = PydanticField(
        default="sqlite",
        description="Storage backend: 'dynamo' or 'sqlite'",
    )

    # AWS (for DynamoDB + S3, or LocalStack)
    aws_endpoint_url: str | None = PydanticField(
        default=None,
        description="AWS endpoint URL (set to http://localhost:4566 for LocalStack)",
    )
    aws_default_region: str = PydanticField(default="us-east-1")
    table_name: str = PydanticField(
        default="wolf-creek-pass", description="DynamoDB table name"
    )
    bucket_name: str = PydanticField(
        default="wolf-creek-pass", description="S3 bucket name"
    )

    model_config = {"env_file": ".env", "env_file_encoding": "utf-8", "extra": "ignore"}
