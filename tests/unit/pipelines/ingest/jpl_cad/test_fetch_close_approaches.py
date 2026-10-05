"""Unit tests for pipelines.ingest.jpl_cad.fetch_close_approaches.

HTTP is mocked with `responses` - no network access.
"""

from datetime import UTC, datetime

import pytest
import requests
import responses
from pipelines.ingest.jpl_cad import DEFAULT_BASE_URL, fetch_close_approaches
from responses import matchers


@responses.activate
def test_fetch_close_approaches_parses_api_response(cad_api_response, make_close_approach):
    responses.add(
        responses.GET,
        DEFAULT_BASE_URL,
        json=cad_api_response,
        match=[
            matchers.query_param_matcher(
                {"date-min": "now", "date-max": "+60", "dist-max": "0.05", "body": "Earth"}
            )
        ],
    )

    result = fetch_close_approaches()

    assert result == [
        make_close_approach(),
        make_close_approach(
            des="2025 XY", orbit_id="12", close_approach_jd=2460510.75,
            close_approach_time=datetime(2029, 5, 2, 3, 10, tzinfo=UTC),
            dist_au=0.0399, dist_min_au=None, dist_max_au=None,
            v_rel_kms=9.87, v_inf_kms=None, h_mag=None, body="Earth",
        ),
    ]


@responses.activate
def test_fetch_close_approaches_returns_empty_list_when_no_data(cad_api_response):
    responses.add(responses.GET, DEFAULT_BASE_URL, json={**cad_api_response, "data": []})

    assert fetch_close_approaches() == []


@responses.activate
def test_fetch_close_approaches_raises_on_http_error():
    responses.add(responses.GET, DEFAULT_BASE_URL, status=500)

    with pytest.raises(requests.HTTPError):
        fetch_close_approaches()
