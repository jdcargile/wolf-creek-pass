"""
Wolf Creek Pass -- AWS CDK Stack

Resources:
- DynamoDB table (single-table design with GSI)
- S3 bucket (images, JSON data, Vue static site)
- Lambda function (capture cycle, container image)
- Lambda function (Reolink API, zip deployment)
- EventBridge rule (hourly cron trigger)
- SSM parameters (API keys -- set real values via AWS CLI)
- S3 deployment (Vue frontend static files)
"""

from aws_cdk import (
    CfnOutput,
    Duration,
    RemovalPolicy,
    Stack,
    aws_dynamodb as dynamodb,
    aws_events as events,
    aws_events_targets as targets,
    aws_iam as iam,
    aws_lambda as lambda_,
    aws_s3 as s3,
    aws_s3_deployment as s3deploy,
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
            website_error_document="index.html",  # SPA fallback
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

        # ---- SSM Parameters (placeholders -- set actual values via CLI) ----
        # After deploy, set real values:
        #   aws ssm put-parameter --name /wolf-creek-pass/udot-api-key --value YOUR_KEY --type String --overwrite
        udot_param = ssm.StringParameter(
            self,
            "UdotApiKeyParam",
            parameter_name="/wolf-creek-pass/udot-api-key",
            string_value="REPLACE_ME",
            description="UDOT Traffic API key",
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

        # Grant Lambda access to DynamoDB, S3, and SSM
        table.grant_read_write_data(capture_fn)
        bucket.grant_read_write(capture_fn)
        udot_param.grant_read(capture_fn)

        # ---- EventBridge Rule (hourly) ----
        events.Rule(
            self,
            "HourlyCaptureRule",
            rule_name="wolf-creek-hourly-capture",
            schedule=events.Schedule.rate(Duration.hours(3)),
            targets=[targets.LambdaFunction(capture_fn)],
        )

        # ---- Reolink API Lambda ----
        # Lightweight Lambda that queries reolink-snapshots DynamoDB for camera
        # snapshots and calls the SensorPush Cloud API directly for sensor data.

        # SSM parameters for SensorPush credentials
        # After deploy, set real values:
        #   aws ssm put-parameter --name /wolf-creek-pass/sensorpush-email --value YOUR_EMAIL --type String --overwrite
        #   aws ssm put-parameter --name /wolf-creek-pass/sensorpush-password --value YOUR_PASS --type SecureString --overwrite
        sp_email_param = ssm.StringParameter(
            self,
            "SensorPushEmailParam",
            parameter_name="/wolf-creek-pass/sensorpush-email",
            string_value="REPLACE_ME",
            description="SensorPush account email",
        )
        sp_password_param = ssm.StringParameter(
            self,
            "SensorPushPasswordParam",
            parameter_name="/wolf-creek-pass/sensorpush-password",
            string_value="REPLACE_ME",
            description="SensorPush account password",
        )

        reolink_fn = lambda_.Function(
            self,
            "ReolinkApiFn",
            function_name="wolf-creek-reolink-api",
            runtime=lambda_.Runtime.PYTHON_3_12,
            handler="handler.handler",
            code=lambda_.Code.from_asset("../reolink_api"),
            timeout=Duration.seconds(60),
            memory_size=128,
            environment={
                "REOLINK_TABLE": "reolink-snapshots",
                "REOLINK_BUCKET": "rl-snapshots",
                "AWS_DEFAULT_REGION": "us-east-1",
                "SENSORPUSH_EMAIL": sp_email_param.string_value,
                "SENSORPUSH_PASSWORD": sp_password_param.string_value,
            },
        )

        # Grant read access to reolink-snapshots table only
        reolink_fn.add_to_role_policy(
            iam.PolicyStatement(
                actions=["dynamodb:Query"],
                resources=[
                    f"arn:aws:dynamodb:us-east-1:{self.account}:table/reolink-snapshots",
                ],
            )
        )

        # Function URL (public HTTPS endpoint with CORS -- no API Gateway needed)
        reolink_url = reolink_fn.add_function_url(
            auth_type=lambda_.FunctionUrlAuthType.NONE,
            cors=lambda_.FunctionUrlCorsOptions(
                allowed_origins=["*"],
                allowed_methods=[lambda_.HttpMethod.GET],
                allowed_headers=["Content-Type"],
                max_age=Duration.hours(24),
            ),
        )

        # ---- Vue Frontend Deployment ----
        # Deploy built Vue assets to S3 under the root prefix
        # Build frontend first: cd frontend && npm run build
        s3deploy.BucketDeployment(
            self,
            "DeployVueFrontend",
            sources=[s3deploy.Source.asset("../frontend/dist")],
            destination_bucket=bucket,
            # Don't delete data/ and images/ when deploying frontend
            prune=False,
        )

        # ---- Outputs ----
        CfnOutput(
            self,
            "WebsiteUrl",
            value=bucket.bucket_website_url,
            description="Wolf Creek Pass dashboard URL",
        )

        CfnOutput(
            self,
            "BucketName",
            value=bucket.bucket_name,
            description="S3 bucket name",
        )

        CfnOutput(
            self,
            "TableName",
            value=table.table_name,
            description="DynamoDB table name",
        )

        CfnOutput(
            self,
            "ReolinkApiUrl",
            value=reolink_url.url,
            description="Reolink API Lambda Function URL",
        )
