"""Tests for upsert_donki_events function."""

import json
from unittest.mock import MagicMock

import pytest

from pipelines.ingest.donki import DonkiEvent, upsert_donki_events


class TestUpsertDonkiEvents:
    """Tests for upsert_donki_events function."""

    def test_returns_zero_without_records(self):
        assert upsert_donki_events(None, []) == 0

    def test_writes_json_payload_and_commits(self, mock_connection, cme_payload):
        record = DonkiEvent.from_api_record(
            "CME", cme_payload[0], "https://example.test/CME"
        )

        count = upsert_donki_events(mock_connection, [record])

        assert count == 1
        sql, params = mock_connection.mock_cursor.executemany.call_args.args
        assert "ON CONFLICT (event_type, event_id) DO UPDATE" in sql
        assert params[0]["event_type"] == "CME"
        assert params[0]["event_id"] == cme_payload[0]["activityID"]
        assert '"sourceLocation":"N28W25"' in params[0]["payload"]
        mock_connection.commit.assert_called_once()

    def test_multiple_records_batched(self, mock_connection, cme_payload):
        record1 = DonkiEvent.from_api_record(
            "CME", cme_payload[0], "https://example.test/CME"
        )
        record2 = DonkiEvent.from_api_record(
            "CME", cme_payload[1], "https://example.test/CME"
        )

        count = upsert_donki_events(mock_connection, [record1, record2])

        assert count == 2
        sql, params = mock_connection.mock_cursor.executemany.call_args.args
        assert len(params) == 2
        assert params[0]["event_id"] == cme_payload[0]["activityID"]
        assert params[1]["event_id"] == cme_payload[1]["activityID"]

    def test_payload_serialized_as_json_string(self, mock_connection, cme_payload):
        record = DonkiEvent.from_api_record(
            "CME", cme_payload[0], "https://example.test/CME"
        )

        upsert_donki_events(mock_connection, [record])

        sql, params = mock_connection.mock_cursor.executemany.call_args.args
        payload_str = params[0]["payload"]
        # Should be a JSON string, not a dict
        assert isinstance(payload_str, str)
        parsed = json.loads(payload_str)
        assert parsed["sourceLocation"] == "N28W25"

    def test_upsert_includes_all_columns(self, mock_connection, cme_payload):
        record = DonkiEvent.from_api_record(
            "CME", cme_payload[0], "https://example.test/CME"
        )

        upsert_donki_events(mock_connection, [record])

        sql, params = mock_connection.mock_cursor.executemany.call_args.args
        # Verify all expected columns are in the INSERT
        assert "event_type" in sql
        assert "event_id" in sql
        assert "start_time" in sql
        assert "end_time" in sql
        assert "event_time" in sql
        assert "source_url" in sql
        assert "payload" in sql
        # Verify ON CONFLICT updates the right columns
        assert "start_time = EXCLUDED.start_time" in sql
        assert "end_time = EXCLUDED.end_time" in sql
        assert "event_time = EXCLUDED.event_time" in sql
        assert "fetched_at = now()" in sql
        assert "source_url = EXCLUDED.source_url" in sql
        assert "payload = EXCLUDED.payload" in sql

    def test_different_event_types_upserted_together(self, mock_connection, cme_payload, sep_payload):
        cme_record = DonkiEvent.from_api_record(
            "CME", cme_payload[0], "https://example.test/CME"
        )
        sep_record = DonkiEvent.from_api_record(
            "SEP", sep_payload[0], "https://example.test/SEP"
        )

        count = upsert_donki_events(mock_connection, [cme_record, sep_record])

        assert count == 2
        sql, params = mock_connection.mock_cursor.executemany.call_args.args
        assert params[0]["event_type"] == "CME"
        assert params[1]["event_type"] == "SEP"