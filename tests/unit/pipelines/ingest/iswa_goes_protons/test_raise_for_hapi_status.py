"""Unit tests for pipelines.ingest.iswa_goes_protons._raise_for_hapi_status.

HTTP is mocked with `responses` - no network access.
"""

import pytest
import requests
import responses
from pipelines.ingest.iswa_goes_protons import _raise_for_hapi_status

URL = "https://hapi.example.test/data"


def _get(**kwargs):
    responses.add(responses.GET, URL, **kwargs)
    return requests.get(URL, timeout=5)


@pytest.mark.parametrize("code", [1200, 1201])
@responses.activate
def test_raise_for_hapi_status_accepts_ok_codes(code):
    _raise_for_hapi_status(_get(json={"status": {"code": code, "message": "OK"}}))


@responses.activate
def test_raise_for_hapi_status_raises_hapi_error_even_with_http_200():
    response = _get(json={"status": {"code": 1406, "message": "Bad request - unknown dataset id"}})

    with pytest.raises(RuntimeError, match="1406"):
        _raise_for_hapi_status(response)


@responses.activate
def test_raise_for_hapi_status_raises_http_error_for_non_json_failure():
    response = _get(status=503, body="Service Unavailable")

    with pytest.raises(requests.HTTPError):
        _raise_for_hapi_status(response)


@responses.activate
def test_raise_for_hapi_status_raises_when_ok_response_has_no_status():
    response = _get(json={"data": []})

    with pytest.raises(RuntimeError, match="no status"):
        _raise_for_hapi_status(response)
