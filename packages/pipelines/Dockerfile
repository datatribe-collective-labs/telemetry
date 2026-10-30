# packages/pipelines/Dockerfile
#
# Build from the REPO ROOT (not from packages/pipelines/), so uv can see the
# workspace and resolve `contracts` as a workspace dependency:
#
#   docker build -f packages/pipelines/Dockerfile -t telemetry-pipelines .
#
# NOTE: no JDK is installed. The pipelines package has no PySpark dependency
# (see pyproject.toml); if PySpark is reintroduced, target Spark 4.x and
# install openjdk-21-jre-headless (Spark 4.x supports Java 17/21/25, but only
# 21 and 25 are packaged on the Debian trixie base).
FROM python:3.12-slim@sha256:a0f57064cbdcd6285fa45f51237ab0b35ea8ebaed06a1f5973e89e19dfb86704 AS base

COPY --from=ghcr.io/astral-sh/uv:0.9.5 /uv /uvx /usr/local/bin/

# Create non-root user up front; COPY --chown avoids a recursive chown layer
RUN useradd --create-home --uid 10001 app && mkdir -p /app && chown app:app /app

WORKDIR /app
USER app

# ---- Copy workspace manifests + sources ----
# (Full sources are needed up front: uv builds real (non-editable) wheels for
# workspace members, which requires their src/ trees.)
COPY --chown=app:app pyproject.toml uv.lock ./
COPY --chown=app:app packages/contracts packages/contracts
COPY --chown=app:app packages/pipelines packages/pipelines

# Resolve + install ONLY pipelines + its deps (contracts, pyspark, kafka...),
# locked to uv.lock. Nothing from backend (fastapi, uvicorn) is pulled in.
RUN uv sync --package pipelines --frozen --no-dev --no-editable

# No CMD by default — this image runs different entrypoints depending on
# which pipeline job it's launched for (ingest, state_engine, kafka_producers,
# etc.), typically set per-Job/CronJob in the k8s manifest, e.g.:
#
#   command: ["/app/.venv/bin/python", "-m", "pipelines.ingest.jpl_horizons"]
