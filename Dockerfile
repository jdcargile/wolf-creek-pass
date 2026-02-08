FROM public.ecr.aws/lambda/python:3.12

# Install dependencies
COPY pyproject.toml ${LAMBDA_TASK_ROOT}/
RUN pip install --no-cache-dir \
    boto3>=1.35.0 \
    click>=8.1.0 \
    polyline>=2.0.0 \
    pydantic>=2.0.0 \
    pydantic-settings>=2.0.0 \
    python-dotenv>=1.0.0 \
    requests>=2.31.0 \
    rich>=13.0.0

# Copy application code
COPY handler.py ${LAMBDA_TASK_ROOT}/
COPY settings.py ${LAMBDA_TASK_ROOT}/
COPY models.py ${LAMBDA_TASK_ROOT}/
COPY storage.py ${LAMBDA_TASK_ROOT}/
COPY route.py ${LAMBDA_TASK_ROOT}/
COPY udot.py ${LAMBDA_TASK_ROOT}/
COPY traffic_cam_monitor.py ${LAMBDA_TASK_ROOT}/
COPY export.py ${LAMBDA_TASK_ROOT}/

CMD ["handler.lambda_handler"]
