"""Fixtures for unit tests of pipelines.ingest.jpl_cad."""

import pytest


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
