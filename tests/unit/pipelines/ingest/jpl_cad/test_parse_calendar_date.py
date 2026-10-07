"""Unit tests for pipelines.ingest.jpl_cad._parse_calendar_date."""

from datetime import UTC, datetime

from pipelines.ingest.jpl_cad import _parse_calendar_date


def test_parse_calendar_date_returns_utc_datetime():
    assert _parse_calendar_date("2029-Apr-13 21:46") == datetime(
        2029, 4, 13, 21, 46, tzinfo=UTC
    )
