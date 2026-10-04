"""Tests for fetch_donki_event_type and fetch_donki_events functions."""

import pytest
import requests
import responses
from responses import matchers

from pipelines.ingest.donki import (
    DEFAULT_BASE_URL,
    EVENT_TYPES,
    fetch_donki_event_type,
    fetch_donki_events,
)


class TestFetchDonkiEventType:
    """Tests for fetch_donki_event_type function."""

    @responses.activate
    def test_uses_correct_endpoint_and_date_parameters(self, cme_payload):
        endpoint = f"{DEFAULT_BASE_URL}/CME"
        responses.add(
            responses.GET,
            endpoint,
            json=cme_payload,
            match=[
                matchers.query_param_matcher(
                    {"startDate": "2026-04-01", "endDate": "2026-04-10"}
                )
            ],
        )

        result = fetch_donki_event_type("CME")

        assert len(result) == 2
        assert result[0].event_id == "2026-04-01T23:45:00-CME-001"
        assert result[1].end_time is not None
        assert responses.calls[0].request.url.startswith(endpoint)

    @responses.activate
    def test_returns_empty_list_for_empty_response(self):
        responses.add(
            responses.GET,
            f"{DEFAULT_BASE_URL}/SEP",
            json=[],
        )

        assert fetch_donki_event_type("SEP") == []

    @responses.activate
    def test_raises_on_http_error(self):
        responses.add(
            responses.GET,
            f"{DEFAULT_BASE_URL}/CME",
            status=500,
        )

        with pytest.raises(requests.HTTPError):
            fetch_donki_event_type("CME")

    def test_rejects_unknown_event_type(self):
        with pytest.raises(ValueError, match="Unsupported DONKI event type"):
            fetch_donki_event_type("NOT_A_DONKI_EVENT")

    @responses.activate
    def test_rejects_non_list_payload(self):
        responses.add(
            responses.GET,
            f"{DEFAULT_BASE_URL}/CME",
            json={"error": "bad payload"},
        )

        with pytest.raises(RuntimeError, match="expected a JSON array"):
            fetch_donki_event_type("CME")

    @responses.activate
    def test_custom_base_url_from_parameter(self, cme_payload):
        custom_url = "https://custom.example.com/DONKI"
        responses.add(
            responses.GET,
            f"{custom_url}/CME",
            json=cme_payload,
            match=[
                matchers.query_param_matcher(
                    {"startDate": "2026-01-01", "endDate": "2026-01-02"}
                )
            ],
        )

        result = fetch_donki_event_type(
            "CME",
            start_date="2026-01-01",
            end_date="2026-01-02",
            base_url=custom_url,
        )

        assert len(result) == 2
        assert responses.calls[0].request.url.startswith(custom_url)

    @responses.activate
    def test_custom_base_url_from_env(self, cme_payload, monkeypatch):
        custom_url = "https://env.example.com/DONKI"
        monkeypatch.setenv("DONKI_BASE_URL", custom_url)

        responses.add(
            responses.GET,
            f"{custom_url}/CME",
            json=cme_payload,
        )

        result = fetch_donki_event_type("CME")

        assert len(result) == 2

    @responses.activate
    def test_all_supported_event_types(self, cme_payload):
        """Test that all EVENT_TYPES can be requested without error."""
        for event_type in EVENT_TYPES:
            responses.add(
                responses.GET,
                f"{DEFAULT_BASE_URL}/{event_type}",
                json=[],
            )

        for event_type in EVENT_TYPES:
            result = fetch_donki_event_type(event_type)
            assert result == []


class TestFetchDonkiEvents:
    """Tests for fetch_donki_events orchestration function."""

    @responses.activate
    def test_fetches_multiple_event_types(self, cme_payload, sep_payload):
        responses.add(
            responses.GET,
            f"{DEFAULT_BASE_URL}/CME",
            json=cme_payload,
        )
        responses.add(
            responses.GET,
            f"{DEFAULT_BASE_URL}/SEP",
            json=sep_payload,
        )

        result = fetch_donki_events(
            start_date="2026-04-01",
            end_date="2026-04-10",
            event_types=("CME", "SEP"),
            request_delay_seconds=0,  # No delay for tests
        )

        assert len(result) == 3  # 2 CME + 1 SEP
        event_types = {r.event_type for r in result}
        assert event_types == {"CME", "SEP"}

    @responses.activate
    def test_defaults_to_all_event_types(self, cme_payload):
        # Add empty responses for all event types first
        for et in EVENT_TYPES:
            responses.add(
                responses.GET,
                f"{DEFAULT_BASE_URL}/{et}",
                json=[],
            )
        # Then override CME with actual payload (responses matches in order)
        responses.replace(
            responses.GET,
            f"{DEFAULT_BASE_URL}/CME",
            json=cme_payload,
        )

        result = fetch_donki_events(request_delay_seconds=0)

        assert len(result) == 2

    @responses.activate
    def test_respects_request_delay(self, cme_payload, sep_payload):
        import time

        responses.add(responses.GET, f"{DEFAULT_BASE_URL}/CME", json=cme_payload)
        responses.add(responses.GET, f"{DEFAULT_BASE_URL}/SEP", json=sep_payload)

        start = time.monotonic()
        fetch_donki_events(
            event_types=("CME", "SEP"),
            request_delay_seconds=0.05,
        )
        elapsed = time.monotonic() - start

        # Should have slept at least once (between the two requests)
        assert elapsed >= 0.04

    @responses.activate
    def test_skips_delay_after_last_request(self, cme_payload, sep_payload):
        import time

        responses.add(responses.GET, f"{DEFAULT_BASE_URL}/CME", json=cme_payload)
        responses.add(responses.GET, f"{DEFAULT_BASE_URL}/SEP", json=sep_payload)

        start = time.monotonic()
        fetch_donki_events(
            event_types=("CME", "SEP"),
            request_delay_seconds=0.05,
        )
        elapsed = time.monotonic() - start

        # Should not sleep after the last request
        assert elapsed < 0.1

    def test_empty_event_types_returns_empty_list(self):
        result = fetch_donki_events(event_types=(), request_delay_seconds=0)
        assert result == []