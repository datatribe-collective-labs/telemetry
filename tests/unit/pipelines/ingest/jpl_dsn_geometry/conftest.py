"""Fixtures for unit tests of pipelines.ingest.jpl_dsn_geometry."""

from datetime import UTC, datetime
from unittest.mock import MagicMock

import pytest
from pipelines.ingest.jpl_dsn_geometry import DSN_SITES, DsnSiteGeometry

# Trimmed from a real Horizons OBSERVER response for -1024 seen from DSS-14
# (QUANTITIES='4,20,21', CSV_FORMAT=YES). The last row is synthetic: Horizons
# prints `n.a.` where a quantity can't be computed.
OBSERVER_RESULT = """\
*******************************************************************************
Target body name: Artemis II (spacecraft) (-1024)
Center body name: Earth (399)                     {source: DE441}
Center-site name: (user defined site below)
*******************************************************************************
Table format    : Comma Separated Values (spreadsheet)
************************************************************************************************
 Date__(UT)__HR:MN, , ,Azi_(a-app), Elev_(a-app),             delta,     deldot,  1-way_down_LT,
************************************************************************************************
$$SOE
 2026-Apr-05 09:00, , , 112.402810,    18.312345,  0.00220540000000, -0.4123456,     0.01834830,
 2026-Apr-05 15:00,*, , 251.706543,     8.412311,  0.00232250000000,  0.6012345,     0.01931580,
 2026-Apr-05 18:00,*,m,       n.a.,         n.a.,              n.a.,       n.a.,           n.a.,
$$EOE
*******************************************************************************
"""


@pytest.fixture
def observer_result():
    return OBSERVER_RESULT


@pytest.fixture
def goldstone():
    return DSN_SITES["DSS-14"]


@pytest.fixture
def make_geometry():
    """Factory for a valid DsnSiteGeometry; pass keyword overrides per test."""

    def _make(**overrides) -> DsnSiteGeometry:
        defaults = {
            "target_id": "-1024",
            "site": "DSS-14",
            "complex": "Goldstone",
            "epoch": datetime(2026, 4, 5, 9, 0, tzinfo=UTC),
            "azimuth_deg": 112.40281,
            "elevation_deg": 18.312345,
            "range_km": 329922.0,
            "range_rate_kms": -0.4123456,
            "light_time_s": 1.100898,
            "visible": True,
        }
        defaults.update(overrides)
        return DsnSiteGeometry(**defaults)

    return _make


@pytest.fixture
def mock_connection():
    """A MagicMock psycopg connection; its cursor is `conn.mock_cursor`."""
    cursor = MagicMock()
    conn = MagicMock()
    conn.cursor.return_value.__enter__.return_value = cursor
    conn.mock_cursor = cursor
    return conn
