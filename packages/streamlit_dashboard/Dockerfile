# packages/streamlit_dashboard/Dockerfile
#
# Build from the REPO ROOT (not from packages/streamlit_dashboard/), so uv
# can see the workspace:
#
#   docker build -f packages/streamlit_dashboard/Dockerfile -t telemetry-streamlit-dashboard .
#
FROM python:3.12-slim AS base

COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /usr/local/bin/

WORKDIR /app

# ---- Copy only what's needed to resolve deps first (better layer caching) ----
COPY pyproject.toml uv.lock ./
COPY packages/streamlit_dashboard/pyproject.toml packages/streamlit_dashboard/pyproject.toml

RUN uv sync --package streamlit_dashboard --frozen --no-dev --no-install-project

# ---- Now copy actual source and install the package itself ----
COPY packages/streamlit_dashboard packages/streamlit_dashboard

RUN uv sync --package streamlit_dashboard --frozen --no-dev

EXPOSE 8501

CMD ["uv", "run", "--package", "streamlit_dashboard", "streamlit", "run", \
     "packages/streamlit_dashboard/src/streamlit_dashboard/app.py", \
     "--server.address=0.0.0.0", "--server.port=8501"]