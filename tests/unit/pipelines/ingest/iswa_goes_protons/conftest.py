"""Fixtures for unit tests of pipelines.ingest.iswa_goes_protons."""

from datetime import UTC, datetime
from unittest.mock import MagicMock

import pytest
from pipelines.ingest.iswa_goes_protons import GoesProtonFlux


@pytest.fixture
def make_goes_proton_flux():
    """Factory for a valid GoesProtonFlux; pass keyword overrides per test."""

    def _make(**overrides) -> GoesProtonFlux:
        defaults = {
            "time": datetime(2026, 4, 1, 22, 0, tzinfo=UTC),
            "proton_satellite": "GOES-18",
            "p1_pfu": 463.37,
            "p5_pfu": 3.23,
            "p10_pfu": 0.34,
            "p30_pfu": 0.158,
            "p50_pfu": 0.153,
            "p60_pfu": 0.151,
            "p100_pfu": 0.149,
            "p500_pfu": 0.140,
        }
        defaults.update(overrides)
        return GoesProtonFlux(**defaults)

    return _make


@pytest.fixture
def mock_connection():
    """A MagicMock psycopg connection; its cursor is `conn.mock_cursor`."""
    cursor = MagicMock()
    conn = MagicMock()
    conn.cursor.return_value.__enter__.return_value = cursor
    conn.mock_cursor = cursor
    return conn


@pytest.fixture
def hapi_response():
    """A small, realistic sample of the iSWA HAPI JSON response: a header of
    parameter definitions (with HAPI's string fill values) plus positional
    data rows. The second row uses every fill form the dataset produces -
    numeric -100000, the string "null", and satellite "-1".
    """
    flux_units = "Protons/cm^2 - s^-1 - sr"
    return {
        "HAPI": "2.0",
        "status": {"code": 1200, "message": "OK"},
        "parameters": [
            {"name": "Time", "type": "isotime", "units": "UTC", "fill": "null", "length": 22},
            {"name": "P1", "type": "double", "units": flux_units, "fill": "-100000"},
            {"name": "P5", "type": "double", "units": flux_units, "fill": "-100000"},
            {"name": "P10", "type": "double", "units": flux_units, "fill": "-100000"},
            {"name": "P30", "type": "double", "units": flux_units, "fill": "-100000"},
            {"name": "P50", "type": "double", "units": flux_units, "fill": "-100000"},
            {"name": "P100", "type": "double", "units": flux_units, "fill": "-100000"},
            {"name": "P60", "type": "double", "units": flux_units, "fill": "null"},
            {"name": "P500", "type": "double", "units": flux_units, "fill": "null"},
            {"name": "satelliteProton", "type": "string", "units": "identifier", "fill": "-1"},
        ],
        "format": "json",
        "data": [
            ["2026-04-01T22:00:00Z", 463.37, 3.23, 0.34, 0.158, 0.153, 0.149, 0.151, 0.140, "GOES-18"],
            ["2026-04-01T22:05:00Z", -100000, 3.11, 0.33, 0.157, 0.152, 0.148, "null", None, "-1"],
        ],
    }
