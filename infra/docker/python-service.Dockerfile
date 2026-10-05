# Shared base for all Python microservices
FROM python:3.11-slim

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential curl \
    && rm -rf /var/lib/apt/lists/*

COPY pyproject.toml ./
RUN pip install --upgrade pip && pip install -e .

COPY services ./services
COPY ml ./ml
COPY scripts ./scripts
COPY config ./config

# default healthcheck for HTTP services (worker services override it)
HEALTHCHECK --interval=15s --timeout=5s --retries=5 \
    CMD curl -fsS http://localhost:${SERVICE_PORT:-8000}/health || exit 1

CMD ["python", "-c", "print('override command in docker-compose')"]
