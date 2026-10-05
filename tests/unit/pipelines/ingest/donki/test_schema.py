"""Tests for ensure_donki_events_table function."""



from pipelines.ingest.donki import DONKI_EVENTS_SCHEMA, ensure_donki_events_table


class TestEnsureDonkiEventsTable:
    """Tests for ensure_donki_events_table function."""

    def test_creates_schema_and_indexes(self, mock_connection):
        mock_connection.mock_cursor.fetchone.return_value = None  # No TimescaleDB

        ensure_donki_events_table(mock_connection)

        executed = [call.args[0] for call in mock_connection.mock_cursor.execute.call_args_list]
        assert DONKI_EVENTS_SCHEMA in executed
        assert any("CREATE INDEX IF NOT EXISTS idx_donki_events_start_time" in sql for sql in executed)
        assert any("CREATE INDEX IF NOT EXISTS idx_donki_events_event_type_time" in sql for sql in executed)
        mock_connection.commit.assert_called_once()

    def test_checks_for_timescaledb_extension(self, mock_connection):
        mock_connection.mock_cursor.fetchone.return_value = None

        ensure_donki_events_table(mock_connection)

        executed = [call.args[0] for call in mock_connection.mock_cursor.execute.call_args_list]
        assert any("pg_extension" in sql and "timescaledb" in sql for sql in executed)

    def test_does_not_create_hypertable_when_timescaledb_absent(self, mock_connection):
        mock_connection.mock_cursor.fetchone.return_value = None

        ensure_donki_events_table(mock_connection)

        executed = [call.args[0] for call in mock_connection.mock_cursor.execute.call_args_list]
        # Should not attempt to create hypertable
        assert not any("create_hypertable" in sql for sql in executed)

    def test_does_not_create_hypertable_per_design(self, mock_connection):
        """
        Per the module docstring, DONKI events are kept as a regular table
        until correlation model has a stable time key.
        """
        mock_connection.mock_cursor.fetchone.return_value = (1,)  # TimescaleDB present

        ensure_donki_events_table(mock_connection)

        executed = [call.args[0] for call in mock_connection.mock_cursor.execute.call_args_list]
        # Currently we don't create hypertable even if TimescaleDB is present
        # This is by design - see comment in ensure_donki_events_table
        assert not any("create_hypertable" in sql for sql in executed)