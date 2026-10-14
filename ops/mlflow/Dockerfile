FROM python:3.12.12-slim-bookworm
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1
COPY backend/requirements-mlflow.lock /app/requirements-mlflow.lock
RUN pip install --no-cache-dir -r /app/requirements-mlflow.lock
ENV MLFLOW_DISABLE_TELEMETRY=true
WORKDIR /app
COPY ops/mlflow/start.py /app/start.py
CMD ["python", "start.py"]
