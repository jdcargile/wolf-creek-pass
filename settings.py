"""Application settings loaded from environment / .env file."""

from pydantic import Field
from pydantic_settings import BaseSettings


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
