# airflow/Dockerfile
#
# Airflow 3 (LocalExecutor) that schedules the real-data ingest jobs.
# Build from the REPO ROOT, so uv can see the workspace and resolve `contracts`:
#
#   docker build -f airflow/Dockerfile -t telemetry-airflow .
#
# `pipelines` is installed into its OWN virtual env (/opt/pipelines/.venv), built
# on the image's base interpreter, not into Airflow's env: pandas, psycopg and
# pdfplumber stay locked to uv.lock and never fight Airflow's pinned deps. The
# DAGs run each ingest module as `<that venv>/bin/python -m pipelines.ingest.<source>`.
FROM apache/airflow:slim-3.3.2-python3.12@sha256:a54e7bd6c4d7a17e55cd14b0ead257877b8f8111680d2692cbdba2ff32bd3ff3 AS runtime

# Extras the slim image lacks, pinned by Airflow's constraints file:
# - postgres: metadata DB drivers, psycopg2 and asyncpg (Airflow 3 opens a sync and an
#   async engine)
# - fab: the FAB auth manager (real users and roles). The default SimpleAuthManager
#   "should not be used in production" (its own docstring).
RUN pip install --no-cache-dir "apache-airflow[postgres,fab]==3.3.2" \
    --constraint "https://raw.githubusercontent.com/apache/airflow/constraints-3.3.2/constraints-3.12.txt"

# ---- pipelines venv ----
USER root
COPY --from=ghcr.io/astral-sh/uv:0.9.5 /uv /usr/local/bin/uv
WORKDIR /opt/pipelines
COPY pyproject.toml uv.lock ./
COPY packages/contracts packages/contracts
COPY packages/pipelines packages/pipelines
# nasa_oem reads this zip by its repo-relative path; the DAG tasks run from /opt/pipelines.
COPY data/oem/all-artemis-ii-oem-files.zip data/oem/all-artemis-ii-oem-files.zip
# /usr/python is the image's base interpreter (Airflow itself lives in a venv on top of it).
RUN UV_PYTHON_DOWNLOADS=never UV_LINK_MODE=copy UV_COMPILE_BYTECODE=1 \
    uv sync --package pipelines --frozen --no-dev --no-editable --python /usr/python/bin/python3.12 \
    && rm -rf /root/.cache/uv

USER airflow
WORKDIR /opt/airflow
COPY --chown=airflow:root airflow/dags /opt/airflow/dags

# ---- test target: the DAG unit tests (compose service `airflow-tests`, profile "test") ----
FROM runtime AS test
# Same pytest as uv.lock; installed into Airflow's env, which the DAG tests need.
RUN pip install --no-cache-dir "pytest==9.1.1"
