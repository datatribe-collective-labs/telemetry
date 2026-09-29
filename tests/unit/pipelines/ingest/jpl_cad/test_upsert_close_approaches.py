"""Unit tests for pipelines.ingest.jpl_cad.upsert_close_approaches.

The connection is mocked - no database.
"""

from pipelines.ingest.jpl_cad import upsert_close_approaches


def test_upsert_close_approaches_returns_zero_for_empty_list_without_db():
    assert upsert_close_approaches(conn=None, records=[]) == 0


def test_upsert_close_approaches_writes_all_records_and_commits(
    mock_connection, make_close_approach
):
    records = [
        make_close_approach(des="2024 AB"),
        make_close_approach(des="2025 XY", orbit_id="12"),
    ]

    count = upsert_close_approaches(mock_connection, records)

    assert count == 2
    sql, params = mock_connection.mock_cursor.executemany.call_args.args
    assert "ON CONFLICT (des, orbit_id, close_approach_time) DO UPDATE" in sql
    assert [p["des"] for p in params] == ["2024 AB", "2025 XY"]
    mock_connection.commit.assert_called_once()
