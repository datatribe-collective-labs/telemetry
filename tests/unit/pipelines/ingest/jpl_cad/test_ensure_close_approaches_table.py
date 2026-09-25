"""Unit tests for pipelines.ingest.jpl_cad.ensure_close_approaches_table.

The connection is mocked - no database. Database-backed behavior is covered
in tests/integration/.
"""

from unittest.mock import MagicMock

from pipelines.ingest.jpl_cad import (
    CLOSE_APPROACHES_HYPERTABLE,
    CLOSE_APPROACHES_SCHEMA,
    ensure_close_approaches_table,
)


def test_ensure_close_approaches_table_skips_hypertable_without_timescaledb():
    """timescaledb isn't installed -> falls back to a plain table, no crash."""
    cursor = MagicMock()
    cursor.fetchone.return_value = None
    conn = MagicMock()
    conn.cursor.return_value.__enter__.return_value = cursor

    ensure_close_approaches_table(conn)

    executed_sql = [call.args[0] for call in cursor.execute.call_args_list]
    assert CLOSE_APPROACHES_SCHEMA in executed_sql
    assert CLOSE_APPROACHES_HYPERTABLE not in executed_sql
    conn.commit.assert_called_once()
