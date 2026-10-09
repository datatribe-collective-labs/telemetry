"""Unit tests for pipelines.ingest.jpl_dsn_geometry.upsert_dsn_site_geometry.

The connection is mocked - no database.
"""

from pipelines.ingest.jpl_dsn_geometry import upsert_dsn_site_geometry


def test_upsert_dsn_site_geometry_returns_zero_for_empty_list_without_db():
    assert upsert_dsn_site_geometry(conn=None, records=[]) == 0


def test_upsert_dsn_site_geometry_writes_all_records_and_commits(
    mock_connection, make_geometry
):
    records = [
        make_geometry(site="DSS-14", complex="Goldstone"),
        make_geometry(site="DSS-43", complex="Canberra", visible=False),
    ]

    count = upsert_dsn_site_geometry(mock_connection, records)

    assert count == 2
    sql, params = mock_connection.mock_cursor.executemany.call_args.args
    assert "ON CONFLICT (target_id, site, epoch) DO UPDATE" in sql
    assert [p["site"] for p in params] == ["DSS-14", "DSS-43"]
    assert [p["visible"] for p in params] == [True, False]
    mock_connection.commit.assert_called_once()
