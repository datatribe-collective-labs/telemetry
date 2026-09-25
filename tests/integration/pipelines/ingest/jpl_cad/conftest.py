"""Fixtures for integration tests of pipelines.ingest.jpl_cad.

These tests need a real database - they talk to the ephemeral
`timescaledb_test` Docker service, never the dev `timescaledb` one. Bring it
up with:

    docker compose up -d timescaledb_test

If it isn't reachable, these tests are skipped (not errored) with a message
telling you how to start it.
"""

import os
import time

import psycopg
import pytest

from pipelines.ingest.jpl_cad import ensure_close_approaches_table

DEFAULT_TEST_DATABASE_URL = "postgresql://telemetry:telemetry@localhost:5434/telemetry_test"

# Deliberately NOT using pipelines.db.get_connection() here - it reads
# DATABASE_URL, which defaults to the dev database. Tests must only ever be
# able to reach TEST_DATABASE_URL.
_TEST_DATABASE_URL = os.environ.get("TEST_DATABASE_URL", DEFAULT_TEST_DATABASE_URL)


@pytest.fixture(scope="session")
def db_connection():
    """A connection to the test database, or a skip if it isn't reachable.

    connect_timeout is required here: without it, connecting to a closed port
    can hang far longer than you'd expect (particularly on Windows, where a
    refused connection doesn't fail fast) - so the retry loop below could
    otherwise stack multiple multi-minute hangs instead of failing quickly.
    """
    last_error = None
    for _ in range(3):
        try:
            conn = psycopg.connect(_TEST_DATABASE_URL, connect_timeout=2)
            break
        except psycopg.OperationalError as exc:
            last_error = exc
            time.sleep(1)
    else:
        pytest.skip(
            f"Could not reach test database at {_TEST_DATABASE_URL} - "
            f"start it with `docker compose up -d timescaledb_test` ({last_error})"
        )

    yield conn
    conn.close()


@pytest.fixture
def clean_close_approaches_table(db_connection):
    """A freshly (re)created, empty `close_approaches` table for one test."""
    with db_connection.cursor() as cur:
        cur.execute("DROP TABLE IF EXISTS close_approaches")
    db_connection.commit()

    ensure_close_approaches_table(db_connection)

    yield db_connection
