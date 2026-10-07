FROM python:3.12-slim

COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /usr/local/bin/

WORKDIR /app
ENV PYTHONPATH=/app/packages/pipelines/src:/app/packages/streamlit_dashboard/src

COPY pyproject.toml uv.lock ./
COPY packages packages
COPY tests tests

RUN uv sync --frozen --no-dev

CMD ["uv", "run", "--package", "streamlit-dashboard", "python", "-m", "unittest", "tests.integration.test_orion_feature", "-v"]