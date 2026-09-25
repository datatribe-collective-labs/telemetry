"""Unit tests for pipelines.ingest.jpl_cad.upsert_close_approaches.

Database-backed behavior is covered in tests/integration/.
"""

from pipelines.ingest.jpl_cad import upsert_close_approaches


def test_upsert_close_approaches_returns_zero_for_empty_list_without_db():
    assert upsert_close_approaches(conn=None, records=[]) == 0
