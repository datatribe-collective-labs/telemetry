"""Unit tests for pipelines.ingest.jpl_dsn_geometry._parse_horizons_date."""

from datetime import UTC, datetime

import pytest
from pipelines.ingest.jpl_dsn_geometry import _parse_horizons_date


@pytest.mark.parametrize(
    "raw, expected",
    [
        ("2026-Apr-05 09:00", datetime(2026, 4, 5, 9, 0, tzinfo=UTC)),
        ("2026-Apr-05 09:00:30", datetime(2026, 4, 5, 9, 0, 30, tzinfo=UTC)),
        ("2026-Apr-05 09:00:30.500", datetime(2026, 4, 5, 9, 0, 30, 500000, tzinfo=UTC)),
        (" A.D. 2026-Apr-05 09:00", datetime(2026, 4, 5, 9, 0, tzinfo=UTC)),
    ],
)
def test_parse_horizons_date_returns_utc_datetime(raw, expected):
    assert _parse_horizons_date(raw) == expected
