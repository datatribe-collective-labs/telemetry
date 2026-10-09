"""Unit tests for pipelines.ingest.jpl_dsn_geometry.ensure_dsn_site_geometry_table.

The connection is mocked - no database.
"""

from pipelines.ingest.jpl_dsn_geometry import (
    DSN_SITE_GEOMETRY_HYPERTABLE,
    DSN_SITE_GEOMETRY_SCHEMA,
    ensure_dsn_site_geometry_table,
)


def _executed_sql(conn):
    return [call.args[0] for call in conn.mock_cursor.execute.call_args_list]


def test_ensure_dsn_site_geometry_table_creates_hypertable_with_timescaledb(mock_connection):
    mock_connection.mock_cursor.fetchone.return_value = (1,)

    ensure_dsn_site_geometry_table(mock_connection)

    executed_sql = _executed_sql(mock_connection)
    assert DSN_SITE_GEOMETRY_SCHEMA in executed_sql
    assert DSN_SITE_GEOMETRY_HYPERTABLE in executed_sql
    mock_connection.commit.assert_called_once()


def test_ensure_dsn_site_geometry_table_skips_hypertable_without_timescaledb(mock_connection):
    """timescaledb isn't installed -> falls back to a plain table, no crash."""
    mock_connection.mock_cursor.fetchone.return_value = None

    ensure_dsn_site_geometry_table(mock_connection)

    executed_sql = _executed_sql(mock_connection)
    assert DSN_SITE_GEOMETRY_SCHEMA in executed_sql
    assert DSN_SITE_GEOMETRY_HYPERTABLE not in executed_sql
    mock_connection.commit.assert_called_once()
