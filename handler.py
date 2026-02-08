"""
AWS Lambda handler for Wolf Creek Pass capture cycle.

Reads API keys from SSM Parameter Store, configures Settings,
and runs a single capture cycle. Triggered hourly by EventBridge.
"""

from __future__ import annotations

import json
import os

import boto3


def lambda_handler(event: dict, context) -> dict:
    """Lambda entry point. Runs one capture cycle."""
    # Read API keys from SSM Parameter Store
    ssm = boto3.client("ssm")
    params = ssm.get_parameters(
        Names=[
            "/wolf-creek-pass/udot-api-key",
        ],
        WithDecryption=True,
    )

    param_map = {p["Name"]: p["Value"] for p in params["Parameters"]}

    # Set env vars so Settings picks them up via pydantic-settings
    os.environ["UDOT_API_KEY"] = param_map.get("/wolf-creek-pass/udot-api-key", "")

    # TABLE_NAME and BUCKET_NAME are set by CDK as Lambda env vars
    os.environ.setdefault("STORAGE_BACKEND", "dynamo")

    from settings import Settings
    from traffic_cam_monitor import run_capture_cycle

    settings = Settings()
    run_capture_cycle(settings)

    return {
        "statusCode": 200,
        "body": json.dumps({"message": "Capture cycle complete"}),
    }
