"""Fixtures for unit tests of pipelines.ingest.jpl_cad."""

from datetime import UTC, datetime
from unittest.mock import MagicMock

import pytest
from pipelines.ingest.jpl_cad import CloseApproach


@pytest.fixture
def make_close_approach():
    """Factory for a valid CloseApproach; pass keyword overrides per test."""

    def _make(**overrides) -> CloseApproach:
        defaults = dict(
            des="2024 AB",
            orbit_id="5",
            close_approach_jd=2460500.5,
            close_approach_time=datetime(2029, 4, 13, 21, 46, tzinfo=UTC),
            dist_au=0.0421,
            dist_min_au=0.0400,
            dist_max_au=0.0450,
            v_rel_kms=12.3,
            v_inf_kms=11.9,
            h_mag=22.1,
            body="Earth",
        )
        defaults.update(overrides)
        return CloseApproach(**defaults)

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
def cad_api_response():
    """A small, realistic sample of what the CAD API returns: a list of field
    names plus parallel rows of string values. The second row omits every
    optional field (as blank strings) to exercise the None/default-fallback
    paths in CloseApproach.from_api_record.
    """
    return {
        "fields": [
            "des", "orbit_id", "jd", "cd",
            "dist", "dist_min", "dist_max", "v_rel", "v_inf", "h", "body",
        ],
        "data": [
            ["2024 AB", "5", "2460500.5", "2029-Apr-13 21:46",
             "0.0421", "0.0400", "0.0450", "12.3", "11.9", "22.1", "Earth"],
            ["2025 XY", "12", "2460510.75", "2029-May-02 03:10",
             "0.0399", "", "", "9.87", "", "", ""],
        ],
    }


@pytest.fixture
def complete_record(cad_api_response):
    """A CAD API record with every field populated."""
    return dict(zip(cad_api_response["fields"], cad_api_response["data"][0]))


@pytest.fixture
def sparse_record(cad_api_response):
    """A CAD API record with every optional field blank."""
    return dict(zip(cad_api_response["fields"], cad_api_response["data"][1]))
