"""Unit tests for pipelines.ingest.iswa_goes_protons._parse_hapi_time."""

from datetime import UTC, datetime

import pytest
from pipelines.ingest.iswa_goes_protons import _parse_hapi_time


@pytest.mark.parametrize("value", ["2026-04-01T22:05:00Z", "2026-04-01T22:05:00.000Z"])
def test_parse_hapi_time_returns_utc_datetime(value):
    assert _parse_hapi_time(value) == datetime(2026, 4, 1, 22, 5, tzinfo=UTC)
