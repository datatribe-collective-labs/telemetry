# packages/backend/Dockerfile
#
# Build from the REPO ROOT (not from packages/backend/), so uv can see the
# workspace and resolve `contracts` as a workspace dependency:
#
#   docker build -f packages/backend/Dockerfile -t telemetry-backend .
#
FROM python:3.12-slim AS base

# uv itself, via the official static binary (fast, no pip bootstrap needed)
COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /usr/local/bin/

WORKDIR /app

# ---- Copy only what's needed to resolve deps first (better layer caching) ----
COPY pyproject.toml uv.lock ./
COPY packages/contracts/pyproject.toml packages/contracts/pyproject.toml
COPY packages/backend/pyproject.toml packages/backend/pyproject.toml

# Resolve + install ONLY backend + its deps (contracts, fastapi, uvicorn...).
# Nothing from pipelines (pyspark, pytorch) is pulled in.
RUN uv sync --package backend --frozen --no-dev --no-install-project

# ---- Now copy actual source and install the packages themselves ----
COPY packages/contracts packages/contracts
COPY packages/backend packages/backend

RUN uv sync --package backend --frozen --no-dev

EXPOSE 8000

CMD ["uv", "run", "--package", "backend", "uvicorn", "backend.api:app", "--host", "0.0.0.0", "--port", "8000"]
