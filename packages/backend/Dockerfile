# packages/backend/Dockerfile
#
# Build from the REPO ROOT (not from packages/backend/), so uv can see the
# workspace and resolve `contracts` as a workspace dependency:
#
#   docker build -f packages/backend/Dockerfile -t telemetry-backend .
#
FROM python:3.12-slim@sha256:a0f57064cbdcd6285fa45f51237ab0b35ea8ebaed06a1f5973e89e19dfb86704 AS base

# uv itself, via the official static binary (fast, no pip bootstrap needed)
COPY --from=ghcr.io/astral-sh/uv:0.9.5 /uv /uvx /usr/local/bin/

WORKDIR /app

# ---- Copy workspace manifests + sources ----
# (Full sources are needed up front: uv builds/bundles workspace members,
# which requires their src/ trees.)
COPY pyproject.toml uv.lock ./
COPY packages/contracts packages/contracts
COPY packages/backend packages/backend

# Resolve + install ONLY backend + its deps (contracts, fastapi, uvicorn...),
# locked to uv.lock. Nothing from pipelines (pyspark, pytorch) is pulled in.
RUN uv sync --package backend --frozen --no-dev --no-editable

# Run as non-root
RUN useradd --create-home --uid 10001 app && chown -R app:app /app
USER app

EXPOSE 8000

CMD ["/app/.venv/bin/uvicorn", "backend.api:app", "--host", "0.0.0.0", "--port", "8000"]
