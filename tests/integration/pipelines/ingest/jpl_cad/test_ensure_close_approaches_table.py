"""Integration tests for pipelines.ingest.jpl_cad.ensure_close_approaches_table.

Need the `timescaledb_test` Docker service (see conftest.py).
"""

import pytest

from pipelines.ingest.jpl_cad import ensure_close_approaches_table

pytestmark = pytest.mark.integration


def test_ensure_close_approaches_table_creates_table(db_connection):
    with db_connection.cursor() as cur:
        cur.execute("DROP TABLE IF EXISTS close_approaches")
    db_connection.commit()

    ensure_close_approaches_table(db_connection)

    with db_connection.cursor() as cur:
        cur.execute(
            "SELECT 1 FROM information_schema.tables WHERE table_name = 'close_approaches'"
        )
        assert cur.fetchone() is not None
