"""Unit tests for pipelines.ingest.iswa_goes_protons.fetch_goes_integral_protons.

HTTP is mocked with `responses` - no network access.
"""

from datetime import UTC, datetime

import pytest
import requests
import responses
from pipelines.ingest.iswa_goes_protons import (
    DEFAULT_BASE_URL,
    fetch_goes_integral_protons,
)
from responses import matchers

DATA_URL = f"{DEFAULT_BASE_URL}/data"


@responses.activate
def test_fetch_goes_integral_protons_parses_api_response(hapi_response, make_goes_proton_flux):
    responses.add(
        responses.GET,
        DATA_URL,
        json=hapi_response,
        match=[
            matchers.query_param_matcher(
                {
                    "id": "goesp_part_flux_P5M",
                    "time.min": "2026-04-01T00:00:00Z",
                    "time.max": "2026-04-12T00:00:00Z",
                    # HAPI rejects parameters out of the dataset's order (error 1411).
                    "parameters": "P1,P5,P10,P30,P50,P100,P60,P500,satelliteProton",
                    "format": "json",
                }
            )
        ],
    )

    result = fetch_goes_integral_protons()

    assert result == [
        make_goes_proton_flux(),
        make_goes_proton_flux(
            time=datetime(2026, 4, 1, 22, 5, tzinfo=UTC),
            proton_satellite=None,
            p1_pfu=None, p5_pfu=3.11, p10_pfu=0.33, p30_pfu=0.157,
            p50_pfu=0.152, p60_pfu=None, p100_pfu=0.148, p500_pfu=None,
        ),
    ]


@responses.activate
def test_fetch_goes_integral_protons_returns_empty_list_when_no_data(hapi_response):
    responses.add(
        responses.GET,
        DATA_URL,
        json={**hapi_response, "status": {"code": 1201, "message": "OK - no data"}, "data": []},
    )

    assert fetch_goes_integral_protons() == []


@responses.activate
def test_fetch_goes_integral_protons_raises_with_hapi_error_message():
    responses.add(
        responses.GET,
        DATA_URL,
        status=400,
        json={"HAPI": "2.0", "status": {"code": 1411, "message": "HAPI error 1411: Parameter out of order"}},
    )

    with pytest.raises(RuntimeError, match="1411.*Parameter out of order"):
        fetch_goes_integral_protons()


@responses.activate
def test_fetch_goes_integral_protons_raises_on_http_error_without_hapi_status():
    responses.add(responses.GET, DATA_URL, status=500, body="Internal Server Error")

    with pytest.raises(requests.HTTPError):
        fetch_goes_integral_protons()


@responses.activate
def test_fetch_goes_integral_protons_uses_base_url_from_env(hapi_response, monkeypatch):
    custom_url = "https://env.example.com/hapi"
    monkeypatch.setenv("ISWA_HAPI_BASE_URL", custom_url)
    responses.add(responses.GET, f"{custom_url}/data", json=hapi_response)

    assert len(fetch_goes_integral_protons()) == 2
