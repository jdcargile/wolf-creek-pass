#!/usr/bin/env python3
"""CDK app entry point for Wolf Creek Pass infrastructure."""

import os

import aws_cdk as cdk

from infra.infra_stack import WolfCreekPassStack

app = cdk.App()
WolfCreekPassStack(
    app,
    "WolfCreekPassStack",
    env=cdk.Environment(
        account=os.getenv("CDK_DEFAULT_ACCOUNT"),
        region=os.getenv("CDK_DEFAULT_REGION", "us-west-2"),
    ),
)

app.synth()
