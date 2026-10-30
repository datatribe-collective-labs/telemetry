# packages/physics_models/Dockerfile
#
# Build from the REPO ROOT (not from packages/physics_models/), so uv can see
# the workspace and resolve `contracts` as a workspace dependency:
#
#   docker build -f packages/physics_models/Dockerfile -t telemetry-physics-models .
#
# Reproducible build: base image pinned by digest, Python deps locked via
# uv.lock (`--frozen`), non-editable installs, non-root runtime user.
FROM python:3.12-slim@sha256:a0f57064cbdcd6285fa45f51237ab0b35ea8ebaed06a1f5973e89e19dfb86704 AS base

# uv itself, via the official static binary (pinned, no pip bootstrap needed)
COPY --from=ghcr.io/astral-sh/uv:0.9.5 /uv /uvx /usr/local/bin/

# NOTE: no gcc / librdkafka-dev needed — the confluent-kafka manylinux wheel
# bundles librdkafka, and psycopg[binary] bundles libpq. All deps install
# from prebuilt wheels.

WORKDIR /app

# ---- Copy workspace manifests + sources ----
# (Full sources are needed up front: uv builds real (non-editable) wheels for
# workspace members, which requires their src/ trees.)
COPY pyproject.toml uv.lock ./
COPY packages/contracts packages/contracts
COPY packages/physics_models packages/physics_models

# NASA OEM ephemeris arcs (state engine ground truth)
COPY data/oem/all-artemis-ii-oem-files.zip /app/oem/all-artemis-ii-oem-files.zip

RUN uv sync --package physics_models --frozen --no-dev --no-editable

# Run as non-root
RUN useradd --create-home --uid 10001 app && chown -R app:app /app
USER app

# Simulator config
ENV PHYSICS_MODELS_CONFIG=/app/packages/physics_models/configs/docker.yaml

CMD ["/app/.venv/bin/python", "packages/physics_models/src/physics_models/runner.py"]
