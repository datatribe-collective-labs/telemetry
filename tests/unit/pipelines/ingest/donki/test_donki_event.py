"""Tests for DonkiEvent dataclass and from_api_record factory."""

from datetime import datetime, timezone

import pytest

from pipelines.ingest.donki import DonkiEvent, _event_id, _stable_payload_id


class TestDonkiEventFromApiRecord:
    """Tests for DonkiEvent.from_api_record factory method."""

    def test_cme_extracts_common_fields(self, cme_payload):
        result = DonkiEvent.from_api_record(
            "CME",
            cme_payload[0],
            "https://ccmc.gsfc.nasa.gov/DONKI-API/get/CME?startDate=2026-04-01&endDate=2026-04-10",
        )

        assert result.event_id == "2026-04-01T23:45:00-CME-001"
        assert result.start_time == datetime(2026, 4, 1, 23, 45, tzinfo=timezone.utc)
        assert result.event_time == result.start_time
        assert result.end_time is None
        assert result.payload["sourceLocation"] == "N28W25"

    def test_cme_with_end_time(self, cme_payload):
        result = DonkiEvent.from_api_record(
            "CME",
            cme_payload[1],
            "https://example.test/CME",
        )

        assert result.end_time == datetime(2026, 4, 2, 5, tzinfo=timezone.utc)

    def test_sep_uses_sep_id_and_event_time(self, sep_payload):
        result = DonkiEvent.from_api_record("SEP", sep_payload[0], "https://example.test/SEP")

        assert result.event_id == "2026-04-01T12:00:00-SEP-001"
        assert result.start_time == datetime(2026, 4, 1, 12, tzinfo=timezone.utc)
        # event_time uses first match: eventTime (12:00) comes before peakTime (14:30)
        assert result.event_time == datetime(2026, 4, 1, 12, tzinfo=timezone.utc)

    def test_flr_uses_flr_id_and_peak_time(self, flr_payload):
        result = DonkiEvent.from_api_record("FLR", flr_payload[0], "https://example.test/FLR")

        assert result.event_id == "2026-04-01T08:00:00-FLR-001"
        assert result.start_time == datetime(2026, 4, 1, 8, tzinfo=timezone.utc)
        assert result.event_time == datetime(2026, 4, 1, 8, 15, tzinfo=timezone.utc)

    def test_gst_uses_gst_id(self, gst_payload):
        result = DonkiEvent.from_api_record("GST", gst_payload[0], "https://example.test/GST")

        assert result.event_id == "2026-04-01T00:00:00-GST-001"
        assert result.start_time == datetime(2026, 4, 1, tzinfo=timezone.utc)

    def test_missing_timestamps_returns_none(self):
        payload = {"activityID": "test-123"}
        result = DonkiEvent.from_api_record("CME", payload, "https://example.test/CME")

        assert result.start_time is None
        assert result.end_time is None
        assert result.event_time is None

    def test_malformed_timestamp_returns_none(self):
        payload = {"activityID": "test-123", "startTime": "not-a-date"}
        result = DonkiEvent.from_api_record("CME", payload, "https://example.test/CME")

        assert result.start_time is None

    def test_z_suffix_timestamp_parsed_as_utc(self):
        payload = {"activityID": "test-123", "startTime": "2026-04-01T12:00Z"}
        result = DonkiEvent.from_api_record("CME", payload, "https://example.test/CME")

        assert result.start_time == datetime(2026, 4, 1, 12, tzinfo=timezone.utc)

    def test_iso_timestamp_with_offset_parsed_correctly(self):
        payload = {"activityID": "test-123", "startTime": "2026-04-01T12:00:00+02:00"}
        result = DonkiEvent.from_api_record("CME", payload, "https://example.test/CME")

        assert result.start_time == datetime(2026, 4, 1, 10, tzinfo=timezone.utc)


class TestEventIdResolution:
    """Tests for _event_id function with type-specific ID fields."""

    def test_cme_prefers_activity_id(self):
        payload = {"activityID": "cme-123", "cmeID": "cme-456"}
        assert _event_id("CME", payload) == "cme-123"

    def test_cme_fallback_to_cme_id(self):
        payload = {"cmeID": "cme-456"}
        assert _event_id("CME", payload) == "cme-456"

    def test_cme_analysis_prefers_activity_id(self):
        payload = {"activityID": "ana-123", "analysisID": "ana-456"}
        assert _event_id("CMEAnalysis", payload) == "ana-123"

    def test_sep_prefers_sep_id(self):
        payload = {"sepID": "sep-123", "activityID": "act-123"}
        assert _event_id("SEP", payload) == "sep-123"

    def test_flr_prefers_flr_id(self):
        payload = {"flrID": "flr-123", "activityID": "act-123"}
        assert _event_id("FLR", payload) == "flr-123"

    def test_unknown_type_falls_back_to_stable_id(self):
        payload = {"customField": "value"}
        result = _event_id("UNKNOWN_TYPE", payload)
        assert result.startswith("sha256:")

    def test_empty_string_id_falls_back_to_next(self):
        payload = {"activityID": "", "cmeID": "cme-789"}
        assert _event_id("CME", payload) == "cme-789"

    def test_none_id_falls_back_to_next(self):
        payload = {"activityID": None, "cmeID": "cme-789"}
        assert _event_id("CME", payload) == "cme-789"


class TestStablePayloadId:
    """Tests for _stable_payload_id deterministic hashing."""

    def test_deterministic_for_same_payload(self):
        payload = {"key": "value", "number": 42}
        id1 = _stable_payload_id(payload)
        id2 = _stable_payload_id(payload)
        assert id1 == id2

    def test_different_for_different_payload(self):
        id1 = _stable_payload_id({"a": 1})
        id2 = _stable_payload_id({"a": 2})
        assert id1 != id2

    def test_order_independent(self):
        id1 = _stable_payload_id({"b": 2, "a": 1})
        id2 = _stable_payload_id({"a": 1, "b": 2})
        assert id1 == id2

    def test_includes_sha256_prefix(self):
        result = _stable_payload_id({"test": "data"})
        assert result.startswith("sha256:")
        assert len(result) == 7 + 64  # "sha256:" + 64 hex chars