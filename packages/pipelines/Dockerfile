# packages/pipelines/Dockerfile
#
# Build from the REPO ROOT (not from packages/pipelines/), so uv can see the
# workspace and resolve `contracts` as a workspace dependency:
#
#   docker build -f packages/pipelines/Dockerfile -t telemetry-pipelines .
#
# This image is expected to be heavy (PySpark, and later PyTorch) — that's
# fine, it's isolated from backend and only rebuilt when pipeline code or
# pipeline deps change.
FROM python:3.12-slim AS base

# Java is required for PySpark
RUN apt-get update \
    && apt-get install -y --no-install-recommends openjdk-17-jre-headless \
    && rm -rf /var/lib/apt/lists/*
ENV JAVA_HOME=/usr/lib/jvm/java-17-openjdk-amd64

COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /usr/local/bin/

WORKDIR /app

# ---- Copy only what's needed to resolve deps first (better layer caching) ----
COPY pyproject.toml uv.lock ./
COPY packages/contracts/pyproject.toml packages/contracts/pyproject.toml
COPY packages/pipelines/pyproject.toml packages/pipelines/pyproject.toml

# Resolve + install ONLY pipelines + its deps (contracts, pyspark, kafka...).
# Nothing from backend (fastapi, uvicorn) is pulled in.
RUN uv sync --package pipelines --frozen --no-dev --no-install-project

# ---- Now copy actual source and install the packages themselves ----
COPY packages/contracts packages/contracts
COPY packages/pipelines packages/pipelines

RUN uv sync --package pipelines --frozen --no-dev

# No CMD by default — this image runs different entrypoints depending on
# which pipeline job it's launched for (ingest, state_engine, kafka_producers,
# etc.), typically set per-Job/CronJob in the k8s manifest, e.g.:
#
#   command: ["uv", "run", "--package", "pipelines", "python", "-m", "pipelines.ingest.jpl_horizons"]
