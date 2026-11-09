# dashboard/Dockerfile - the Digital Twin dashboard (Streamlit)
#
# Build from the REPO ROOT (not from dashboard/), so uv can see the workspace and
# resolve `contracts` as a workspace dependency:
#
#   docker build -f dashboard/Dockerfile -t telemetry-dashboard .
#
# `dashboard` is a virtual workspace member (not built or installed): the app runs
# from its source tree, and pages import each other as `dashboard.src.prototype...`
# from /app (app.py puts the repo root on sys.path).
FROM python:3.12-slim@sha256:a0f57064cbdcd6285fa45f51237ab0b35ea8ebaed06a1f5973e89e19dfb86704 AS base

# uv itself, via the official static binary (pinned, no pip bootstrap needed)
COPY --from=ghcr.io/astral-sh/uv:0.9.5 /uv /uvx /usr/local/bin/

WORKDIR /app

# ---- Copy workspace manifests + sources ----
COPY pyproject.toml uv.lock ./
COPY packages/contracts packages/contracts
COPY dashboard/pyproject.toml dashboard/pyproject.toml
COPY dashboard/src dashboard/src

# Only the dashboard's deps (streamlit, httpx, pandas, plotly, contracts), locked to uv.lock
RUN uv sync --package dashboard --frozen --no-dev --no-editable

# Run as non-root
RUN useradd --create-home --uid 10001 app && chown -R app:app /app
USER app

# The backend's address inside the Compose network (override for other setups)
ENV BACKEND_URL=http://backend:8000 \
    STREAMLIT_BROWSER_GATHER_USAGE_STATS=false

EXPOSE 8501

HEALTHCHECK --interval=10s --timeout=5s --retries=5 \
    CMD ["/app/.venv/bin/python", "-c", "import urllib.request; urllib.request.urlopen('http://localhost:8501/_stcore/health')"]

CMD ["/app/.venv/bin/streamlit", "run", "dashboard/src/prototype/app.py", \
     "--server.port=8501", "--server.address=0.0.0.0", "--server.headless=true"]
