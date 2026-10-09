"""Unit tests for pipelines.ingest.iswa_goes_protons.ensure_goes_integral_protons_table.

The connection is mocked - no database.
"""

from pipelines.ingest.iswa_goes_protons import (
    GOES_INTEGRAL_PROTONS_HYPERTABLE,
    GOES_INTEGRAL_PROTONS_SCHEMA,
    ensure_goes_integral_protons_table,
)


def _executed_sql(conn):
    return [call.args[0] for call in conn.mock_cursor.execute.call_args_list]


def test_ensure_goes_integral_protons_table_creates_hypertable_with_timescaledb(mock_connection):
    mock_connection.mock_cursor.fetchone.return_value = (1,)

    ensure_goes_integral_protons_table(mock_connection)

    executed_sql = _executed_sql(mock_connection)
    assert GOES_INTEGRAL_PROTONS_SCHEMA in executed_sql
    assert GOES_INTEGRAL_PROTONS_HYPERTABLE in executed_sql
    mock_connection.commit.assert_called_once()


def test_ensure_goes_integral_protons_table_skips_hypertable_without_timescaledb(mock_connection):
    """timescaledb isn't installed -> falls back to a plain table, no crash."""
    mock_connection.mock_cursor.fetchone.return_value = None

    ensure_goes_integral_protons_table(mock_connection)

    executed_sql = _executed_sql(mock_connection)
    assert GOES_INTEGRAL_PROTONS_SCHEMA in executed_sql
    assert GOES_INTEGRAL_PROTONS_HYPERTABLE not in executed_sql
    mock_connection.commit.assert_called_once()
