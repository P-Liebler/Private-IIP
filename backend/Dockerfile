FROM python:3.12.12-slim-bookworm AS base

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1
WORKDIR /app
COPY backend/requirements.txt /app/requirements.txt
COPY backend/requirements.lock /app/requirements.lock
RUN pip install --no-cache-dir -r requirements.lock
COPY backend/ /app/

FROM base AS dev
ENV MYPY_CACHE_DIR=/tmp/private-iip-mypy
COPY backend/requirements-dev.txt /app/requirements-dev.txt
COPY backend/requirements-dev.lock /app/requirements-dev.lock
RUN pip install --no-cache-dir -r requirements-dev.lock
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]

FROM base AS production
RUN useradd --create-home --uid 10001 appuser
USER appuser
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
