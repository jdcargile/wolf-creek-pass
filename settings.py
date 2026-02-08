"""Application settings loaded from environment / .env file."""

from pydantic import Field
from pydantic_settings import BaseSettings


# Hardcoded camera IDs along the Riverton -> Hanna route.
# Primary route: I-215 E -> I-80 E (Parley's Canyon) -> US-40 (Heber ->
#   Daniels Summit -> Strawberry) -> SR-35 (Wolf Creek Pass) -> Duchesne
# Alternate: US-189 through Provo Canyon (kept for visibility)
# Selected from UDOT's 2000+ cameras. Only fetch/analyze these.
ROUTE_CAMERA_IDS: list[int] = [
    # --- PRIMARY ROUTE ---
    # I-215 East (Riverton -> I-80)
    91683,  # I-215 S WB @ Union Park Ave
    91581,  # I-215 E NB @ 6400 S
    91614,  # I-215 E NB @ Parleys Canyon / 2900 S
    # I-80 Parley's Canyon (SLC -> Park City)
    91604,  # I-80 EB @ Mouth of Parley's Canyon
    91619,  # I-80 EB @ Chain Up Area East
    91746,  # I-80 EB @ MP 132.97
    91642,  # I-80 EB @ East Canyon / SR-65
    90912,  # I-80 EB @ Parley's Summit
    91410,  # I-80 EB @ Parley's Canyon / MP 138
    91425,  # I-80 EB @ Summit Park
    91761,  # I-80 EB @ View Area
    91736,  # I-80 EB @ West of US-40 junction
    # --- SHARED (both routes merge here) ---
    # Heber Valley -> Daniels Summit (US-40)
    90389,  # US-40 @ US-189 / 1200 S, Heber
    90353,  # US-40 @ 100 S, Heber
    91773,  # US-40 @ Coyote Canyon Pkwy, Heber
    87716,  # US-40 @ Deer Hollow Rd
    90593,  # US-40 @ MP 27.53
    92985,  # US-40 SB @ Lodge Pole / MP 33.43
    90307,  # US-40 @ Daniels Summit
    # Strawberry Reservoir (US-40)
    90207,  # US-40 @ Strawberry Rd
    88216,  # US-40 @ Strawberry Reservoir
    90980,  # US-40 @ Strawberry Reservoir Ladders
    90465,  # US-40 @ MP 49.14
    # Wolf Creek Pass (SR-35) -- the money cameras
    90544,  # SR-35 RWIS @ Wolf Creek / MP 9.92
    90779,  # SR-35 RWIS EB @ Wolf Creek Pass / MP 19.33
    # Duchesne area (US-40)
    90043,  # US-40 @ WA/DU County Line
    90661,  # US-40 @ MP 69.81
    89190,  # US-40 @ 100 W / US-191, Duchesne
    # --- ALTERNATE: Provo Canyon (US-189) ---
    90363,  # US-189 @ Mouth of Provo Canyon
    87874,  # US-189 @ Springdell
    90727,  # US-189 @ Canyon Glen Park
    90626,  # US-189 @ Fishermen's
    90728,  # US-189 @ Lower Deer Creek Rd
    90275,  # US-189 @ Deer Creek Dam
]


class Settings(BaseSettings):
    """All configuration for Wolf Creek Pass, loaded from .env or environment."""

    # API keys
    udot_api_key: str = Field(description="UDOT Traffic API key")
    anthropic_api_key: str = Field(description="Anthropic API key")
    google_maps_api_key: str = Field(default="", description="Google Maps API key")

    # Storage backend
    storage_backend: str = Field(
        default="sqlite",
        description="Storage backend: 'dynamo' or 'sqlite'",
    )

    # AWS (for DynamoDB + S3, or LocalStack)
    aws_endpoint_url: str | None = Field(
        default=None,
        description="AWS endpoint URL (set to http://localhost:4566 for LocalStack)",
    )
    aws_default_region: str = Field(default="us-west-2")
    table_name: str = Field(
        default="wolf-creek-pass", description="DynamoDB table name"
    )
    bucket_name: str = Field(default="wolf-creek-pass", description="S3 bucket name")

    # Route
    origin: str = Field(
        default="3814 Sweet Vera Ln, Riverton, UT 84065",
        description="Route origin address",
    )
    destination: str = Field(
        default="14852 North Fork Rd, Hanna, UT 84031",
        description="Route destination address",
    )
    camera_buffer_km: float = Field(
        default=2.0,
        description="Max distance (km) from route to include a camera",
    )

    model_config = {"env_file": ".env", "env_file_encoding": "utf-8"}
