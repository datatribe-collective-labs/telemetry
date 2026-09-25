"""Integration tests for pipelines.ingest.jpl_cad.upsert_close_approaches.

Need the `timescaledb_test` Docker service (see conftest.py).
"""

import pytest

from pipelines.ingest.jpl_cad import upsert_close_approaches

pytestmark = pytest.mark.integration


def test_upsert_close_approaches_inserts_new_records(
    clean_close_approaches_table, make_close_approach
):
    conn = clean_close_approaches_table
    records = [
        make_close_approach(des="2024 AB"),
        make_close_approach(des="2025 XY", orbit_id="12"),
    ]

    count = upsert_close_approaches(conn, records)

    assert count == 2
    with conn.cursor() as cur:
        cur.execute("SELECT count(*) FROM close_approaches")
        assert cur.fetchone()[0] == 2


def test_upsert_close_approaches_updates_existing_record_on_conflict(
    clean_close_approaches_table, make_close_approach
):
    conn = clean_close_approaches_table
    upsert_close_approaches(conn, [make_close_approach(dist_au=0.0421)])

    upsert_close_approaches(conn, [make_close_approach(dist_au=0.0999)])

    with conn.cursor() as cur:
        cur.execute("SELECT count(*), max(dist_au) FROM close_approaches")
        row_count, dist_au = cur.fetchone()
        assert row_count == 1
        assert dist_au == 0.0999
