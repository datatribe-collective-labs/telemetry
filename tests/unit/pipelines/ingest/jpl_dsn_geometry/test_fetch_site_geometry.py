"""Unit tests for pipelines.ingest.jpl_dsn_geometry.fetch_site_geometry.

HTTP is mocked with `responses` - no network access.
"""

import pytest
import requests
import responses
from pipelines.ingest.jpl_dsn_geometry import DEFAULT_BASE_URL, fetch_site_geometry
from responses import matchers


@responses.activate
def test_fetch_site_geometry_sends_topocentric_observer_query(observer_result, goldstone):
    responses.add(
        responses.GET,
        DEFAULT_BASE_URL,
        json={"result": observer_result},
        match=[
            matchers.query_param_matcher(
                {
                    "format": "json",
                    "COMMAND": "'-1024'",
                    "OBJ_DATA": "NO",
                    "MAKE_EPHEM": "YES",
                    "EPHEM_TYPE": "OBSERVER",
                    "CENTER": "'coord@399'",
                    "COORD_TYPE": "GEODETIC",
                    "SITE_COORD": "'243.1105,35.4259,1.002'",
                    "START_TIME": "'2026-04-02 02:00'",
                    "STOP_TIME": "'2026-04-10 23:00'",
                    "STEP_SIZE": "'1 h'",
                    "QUANTITIES": "'4,20,21'",
                    "ANG_FORMAT": "DEG",
                    "APPARENT": "AIRLESS",
                    "CSV_FORMAT": "YES",
                }
            )
        ],
    )

    records = fetch_site_geometry(goldstone)

    assert len(records) == 3
    assert {r.site for r in records} == {"DSS-14"}


@responses.activate
def test_fetch_site_geometry_raises_on_horizons_error(goldstone):
    responses.add(responses.GET, DEFAULT_BASE_URL, json={"error": "Bad target"})

    with pytest.raises(RuntimeError, match="Bad target"):
        fetch_site_geometry(goldstone)


@responses.activate
def test_fetch_site_geometry_raises_on_http_error(goldstone):
    responses.add(responses.GET, DEFAULT_BASE_URL, status=503)

    with pytest.raises(requests.HTTPError):
        fetch_site_geometry(goldstone)
