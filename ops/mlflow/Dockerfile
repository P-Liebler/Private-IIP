ARG PYTHON_IMAGE=python:3.12.15-slim-trixie@sha256:a6e34c598f2467ed0e9a8d349809fcd8b5c603269512df273a0bb1784edc11b1
FROM ${PYTHON_IMAGE}
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1
COPY backend/requirements-mlflow.lock /app/requirements-mlflow.lock
RUN pip install --no-cache-dir --no-compile -r /app/requirements-mlflow.lock
ENV MLFLOW_DISABLE_TELEMETRY=true
# Training runs in the application's Celery worker. The tracking server does not
# need MLflow's separate executable job queues or custom scorer execution.
ENV MLFLOW_SERVER_ENABLE_JOB_EXECUTION=false \
    MLFLOW_SERVER_JOB_ENABLE_PERIODIC_TASKS=false \
    MLFLOW_SERVER_ENABLE_CUSTOM_SCORERS=false
WORKDIR /app
COPY ops/mlflow/start.py /app/start.py
RUN useradd --create-home --uid 10001 appuser
ENV HOME=/tmp
USER appuser
CMD ["python", "start.py"]
