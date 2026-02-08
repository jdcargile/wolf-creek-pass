"""Application settings loaded from environment / .env file."""

from __future__ import annotations

from dataclasses import dataclass, field

from pydantic import Field as PydanticField
from pydantic_settings import BaseSettings


# ---------------------------------------------------------------------------
# Route definitions -- 3 named routes from Riverton to Hanna
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
    # ── 1. PRIMARY: Parley's → Kamas → Francis → Wolf Creek Pass ──────
    # JD's preferred commute. I-15 → I-215 → I-80 (Parley's Canyon) →
    # SR-248 to Kamas → SR-32 south through Francis → SR-35 east over
    # Wolf Creek Pass → US-40 to Hanna.
    RouteConfig(
        route_id="parleys-wolfcreek",
        name="Parley's / Wolf Creek",
        waypoints=["Kamas, UT", "Francis, UT"],
        color="#3b82f6",  # blue
        camera_ids=[
            # I-215 East (Riverton → I-80)
            91683,  # I-215 S WB @ Union Park Ave
            91581,  # I-215 E NB @ 6400 S
            91614,  # I-215 E NB @ Parleys Canyon / 2900 S
            # I-80 Parley's Canyon (SLC → Park City)
            91604,  # I-80 EB @ Mouth of Parley's Canyon
            91619,  # I-80 EB @ Chain Up Area East
            91746,  # I-80 EB @ MP 132.97
            91642,  # I-80 EB @ East Canyon / SR-65
            90912,  # I-80 EB @ Parley's Summit
            91410,  # I-80 EB @ Parley's Canyon / MP 138
            91425,  # I-80 EB @ Summit Park
            91761,  # I-80 EB @ View Area
            91736,  # I-80 EB @ West of US-40 junction
            # SR-35 Wolf Creek Pass -- the money cameras
            90544,  # SR-35 RWIS @ Wolf Creek / MP 9.92
            90779,  # SR-35 RWIS EB @ Wolf Creek Pass / MP 19.33
            # US-40 east of Wolf Creek → Duchesne → Hanna
            90043,  # US-40 @ WA/DU County Line
            90661,  # US-40 @ MP 69.81
            89190,  # US-40 @ 100 W / US-191, Duchesne
        ],
    ),
    # ── 2. SECONDARY: Provo Canyon → Kamas → Wolf Creek Pass ──────────
    # US-189 through Provo Canyon → Heber → SR-32 north through Francis
    # to Kamas → SR-35 east over Wolf Creek Pass → US-40 to Hanna.
    RouteConfig(
        route_id="provo-wolfcreek",
        name="Provo Canyon / Wolf Creek",
        waypoints=["Provo Canyon, UT", "Heber City, UT", "Kamas, UT"],
        color="#8b5cf6",  # purple
        camera_ids=[
            # US-189 Provo Canyon
            90363,  # US-189 @ Mouth of Provo Canyon
            87874,  # US-189 @ Springdell
            90727,  # US-189 @ Canyon Glen Park
            90626,  # US-189 @ Fishermen's
            90728,  # US-189 @ Lower Deer Creek Rd
            90275,  # US-189 @ Deer Creek Dam
            # US-40 Heber area (brief segment before SR-32)
            90389,  # US-40 @ US-189 / 1200 S, Heber
            90353,  # US-40 @ 100 S, Heber
            91773,  # US-40 @ Coyote Canyon Pkwy, Heber
            # SR-35 Wolf Creek Pass (shared with primary)
            90544,  # SR-35 RWIS @ Wolf Creek / MP 9.92
            90779,  # SR-35 RWIS EB @ Wolf Creek Pass / MP 19.33
            # US-40 east of Wolf Creek → Duchesne → Hanna (shared)
            90043,  # US-40 @ WA/DU County Line
            90661,  # US-40 @ MP 69.81
            89190,  # US-40 @ 100 W / US-191, Duchesne
        ],
    ),
    # ── 3. TERTIARY: US-40 through Tabiona (Wolf Creek closed) ────────
    # When SR-35 is closed. I-215 → I-80 → US-40 → Heber → Daniels
    # Summit → Strawberry Reservoir → Duchesne → north to Tabiona → Hanna.
    # Bypasses Wolf Creek Pass entirely, stays on US-40.
    RouteConfig(
        route_id="us40-tabiona",
        name="US-40 / Tabiona",
        waypoints=["Duchesne, UT", "Tabiona, UT"],
        color="#f97316",  # orange
        camera_ids=[
            # I-215 East (shared with primary)
            91683,  # I-215 S WB @ Union Park Ave
            91581,  # I-215 E NB @ 6400 S
            91614,  # I-215 E NB @ Parleys Canyon / 2900 S
            # I-80 Parley's Canyon (shared with primary)
            91604,  # I-80 EB @ Mouth of Parley's Canyon
            91619,  # I-80 EB @ Chain Up Area East
            91746,  # I-80 EB @ MP 132.97
            91642,  # I-80 EB @ East Canyon / SR-65
            90912,  # I-80 EB @ Parley's Summit
            91410,  # I-80 EB @ Parley's Canyon / MP 138
            91425,  # I-80 EB @ Summit Park
            91761,  # I-80 EB @ View Area
            91736,  # I-80 EB @ West of US-40 junction
            # US-40 Heber → Daniels Summit
            90389,  # US-40 @ US-189 / 1200 S, Heber
            90353,  # US-40 @ 100 S, Heber
            91773,  # US-40 @ Coyote Canyon Pkwy, Heber
            87716,  # US-40 @ Deer Hollow Rd
            90593,  # US-40 @ MP 27.53
            92985,  # US-40 SB @ Lodge Pole / MP 33.43
            90307,  # US-40 @ Daniels Summit
            # US-40 Strawberry Reservoir
            90207,  # US-40 @ Strawberry Rd
            88216,  # US-40 @ Strawberry Reservoir
            90980,  # US-40 @ Strawberry Reservoir Ladders
            90465,  # US-40 @ MP 49.14
            # US-40 Duchesne area
            90043,  # US-40 @ WA/DU County Line
            90661,  # US-40 @ MP 69.81
            89190,  # US-40 @ 100 W / US-191, Duchesne
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
