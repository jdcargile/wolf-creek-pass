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
    """Static definition of a named route with waypoints and camera IDs."""

    route_id: str
    name: str
    waypoints: list[str] = field(default_factory=list)
    camera_ids: list[int] = field(default_factory=list)
    color: str = "#3b82f6"  # Hex color for map polyline


ROUTES: list[RouteConfig] = [
    # ── PRIMARY: Parley's Canyon → SR-35 Wolf Creek Pass ──────────────
    # I-15 N → I-215 E → I-80 E (Parley's Canyon) → SR-248 to Kamas →
    # SR-32 S to Francis → SR-35 E over Wolf Creek Pass → US-40 to Hanna.
    # ~112 min, ~94 mi per Google Directions.
    #
    # Waypoints use UDOT camera coordinates ON SR-35 to force the route
    # through Wolf Creek Pass (city-name waypoints like "Kamas, UT" let
    # Google shortcut via UT-150 / forest roads).
    RouteConfig(
        route_id="parleys-wolfcreek",
        name="Parley's / Wolf Creek",
        waypoints=[
            "via:40.558,-111.131",  # SR-35 RWIS @ Wolf Creek / MP 9.92
            "via:40.4872,-111.0344",  # SR-35 RWIS EB @ Wolf Creek Pass / MP 19.33
        ],
        color="#3b82f6",  # blue
        camera_ids=[
            # I-80 Parley's Canyon (SLC → Park City) -- key corridor cameras
            91604,  # I-80 EB @ Mouth of Parley's Canyon
            91746,  # I-80 EB @ MP 132.97
            90912,  # I-80 EB @ Parley's Summit
            91736,  # I-80 EB @ West of US-40 junction
            # SR-35 Wolf Creek Pass -- the money cameras
            90544,  # SR-35 RWIS @ Wolf Creek / MP 9.92
            90779,  # SR-35 RWIS EB @ Wolf Creek Pass / MP 19.33
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


def get_route_ids_for_camera(camera_id: int) -> list[str]:
    """Return which route IDs a camera belongs to."""
    return [r.route_id for r in ROUTES if camera_id in r.camera_ids]


class Settings(BaseSettings):
    """All configuration for Wolf Creek Pass, loaded from .env or environment."""

    # API keys
    udot_api_key: str = PydanticField(description="UDOT Traffic API key")
    anthropic_api_key: str = PydanticField(description="Anthropic API key")
    google_maps_api_key: str = PydanticField(
        default="", description="Google Maps API key"
    )

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
    aws_default_region: str = PydanticField(default="us-west-2")
    table_name: str = PydanticField(
        default="wolf-creek-pass", description="DynamoDB table name"
    )
    bucket_name: str = PydanticField(
        default="wolf-creek-pass", description="S3 bucket name"
    )

    # Route
    origin: str = PydanticField(
        default="3814 Sweet Vera Ln, Riverton, UT 84065",
        description="Route origin address",
    )
    destination: str = PydanticField(
        default="14852 North Fork Rd, Hanna, UT 84031",
        description="Route destination address",
    )
    camera_buffer_km: float = PydanticField(
        default=2.0,
        description="Max distance (km) from route to include a camera",
    )

    model_config = {"env_file": ".env", "env_file_encoding": "utf-8"}
