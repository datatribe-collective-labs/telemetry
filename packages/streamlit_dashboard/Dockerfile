# packages/streamlit_dashboard/Dockerfile
#
# Build from the REPO ROOT (not from packages/streamlit_dashboard/), so uv
# can see the workspace:
#
#   docker build -f packages/streamlit_dashboard/Dockerfile -t telemetry-streamlit-dashboard .
#
FROM python:3.12-slim@sha256:a0f57064cbdcd6285fa45f51237ab0b35ea8ebaed06a1f5973e89e19dfb86704 AS base

COPY --from=ghcr.io/astral-sh/uv:0.9.5 /uv /uvx /usr/local/bin/

WORKDIR /app

# ---- Copy only what's needed to resolve deps first (better layer caching) ----
COPY pyproject.toml uv.lock ./
COPY packages/streamlit_dashboard/pyproject.toml packages/streamlit_dashboard/pyproject.toml

RUN uv sync --package streamlit_dashboard --frozen --no-dev --no-install-project

# ---- Now copy actual source and install the package itself ----
COPY packages/streamlit_dashboard packages/streamlit_dashboard

RUN uv sync --package streamlit_dashboard --frozen --no-dev

# Run as non-root
RUN useradd --create-home --uid 10001 app && chown -R app:app /app
USER app

EXPOSE 8501

CMD ["/app/.venv/bin/streamlit", "run", \
     "packages/streamlit_dashboard/src/streamlit_dashboard/app.py", \
     "--server.address=0.0.0.0", "--server.port=8501"]