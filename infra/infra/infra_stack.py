"""
Wolf Creek Pass -- AWS CDK Stack

Resources:
- DynamoDB table (single-table design with GSI)
- S3 bucket (images, JSON data, Vue static site)
- Lambda function (capture cycle, container image)
- EventBridge rule (hourly cron trigger)
- SSM parameters (API keys)
"""

from aws_cdk import (
    Duration,
    RemovalPolicy,
    Stack,
    aws_dynamodb as dynamodb,
    aws_events as events,
    aws_events_targets as targets,
    aws_lambda as lambda_,
    aws_s3 as s3,
    aws_ssm as ssm,
)
from constructs import Construct


class WolfCreekPassStack(Stack):
    def __init__(self, scope: Construct, construct_id: str, **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)

        # ---- DynamoDB Table (single-table design) ----
        table = dynamodb.Table(
            self,
            "WolfCreekTable",
            table_name="wolf-creek-pass",
            partition_key=dynamodb.Attribute(
                name="PK", type=dynamodb.AttributeType.STRING
            ),
            sort_key=dynamodb.Attribute(name="SK", type=dynamodb.AttributeType.STRING),
            billing_mode=dynamodb.BillingMode.PAY_PER_REQUEST,
            removal_policy=RemovalPolicy.RETAIN,
        )

        # GSI1: query by capture cycle
        table.add_global_secondary_index(
            index_name="GSI1",
            partition_key=dynamodb.Attribute(
                name="GSI1PK", type=dynamodb.AttributeType.STRING
            ),
            sort_key=dynamodb.Attribute(
                name="GSI1SK", type=dynamodb.AttributeType.STRING
            ),
            projection_type=dynamodb.ProjectionType.ALL,
        )

        # ---- S3 Bucket ----
        bucket = s3.Bucket(
            self,
            "WolfCreekBucket",
            bucket_name=f"wolf-creek-pass-{self.account}",
            removal_policy=RemovalPolicy.RETAIN,
            website_index_document="index.html",
            public_read_access=True,
            block_public_access=s3.BlockPublicAccess(
                block_public_acls=False,
                block_public_policy=False,
                ignore_public_acls=False,
                restrict_public_buckets=False,
            ),
            cors=[
                s3.CorsRule(
                    allowed_methods=[s3.HttpMethods.GET],
                    allowed_origins=["*"],
                    allowed_headers=["*"],
                )
            ],
        )

        # ---- Lambda Function ----
        capture_fn = lambda_.DockerImageFunction(
            self,
            "CaptureFn",
            function_name="wolf-creek-capture",
            code=lambda_.DockerImageCode.from_image_asset(".."),
            timeout=Duration.minutes(5),
            memory_size=512,
            environment={
                "TABLE_NAME": table.table_name,
                "BUCKET_NAME": bucket.bucket_name,
                "STORAGE_BACKEND": "dynamo",
            },
        )

        # Grant Lambda access to DynamoDB and S3
        table.grant_read_write_data(capture_fn)
        bucket.grant_read_write(capture_fn)

        # ---- EventBridge Rule (hourly) ----
        events.Rule(
            self,
            "HourlyCaptureRule",
            rule_name="wolf-creek-hourly-capture",
            schedule=events.Schedule.rate(Duration.hours(1)),
            targets=[targets.LambdaFunction(capture_fn)],
        )

        # ---- SSM Parameters (placeholders -- set actual values via CLI) ----
        ssm.StringParameter(
            self,
            "UdotApiKeyParam",
            parameter_name="/wolf-creek-pass/udot-api-key",
            string_value="REPLACE_ME",
            description="UDOT Traffic API key",
        )

        ssm.StringParameter(
            self,
            "AnthropicApiKeyParam",
            parameter_name="/wolf-creek-pass/anthropic-api-key",
            string_value="REPLACE_ME",
            description="Anthropic API key",
        )

        ssm.StringParameter(
            self,
            "GoogleMapsApiKeyParam",
            parameter_name="/wolf-creek-pass/google-maps-api-key",
            string_value="REPLACE_ME",
            description="Google Maps API key",
        )
