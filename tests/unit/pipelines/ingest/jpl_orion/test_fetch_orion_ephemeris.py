"""Unit tests for pipelines.ingest.jpl_orion.fetch_orion_ephemeris.

HTTP is mocked with `responses` - no network access.
"""

from datetime import UTC, datetime

import pytest
import requests
import responses
from pipelines.ingest.jpl_orion import DEFAULT_BASE_URL, fetch_orion_ephemeris
from responses import matchers


@responses.activate
def test_fetch_orion_ephemeris_requests_eme2000_ut_vectors(vectors_result):
    responses.add(
        responses.GET,
        DEFAULT_BASE_URL,
        json={"result": vectors_result},
        match=[
            matchers.query_param_matcher(
                {
                    "format": "json",
                    "COMMAND": "'-1024'",
                    "OBJ_DATA": "YES",
                    "MAKE_EPHEM": "YES",
                    "EPHEM_TYPE": "VECTORS",
                    "OUT_UNITS": "'KM-S'",
                    "CENTER": "'500@399'",
                    "REF_PLANE": "FRAME",
                    "REF_SYSTEM": "ICRF",
                    "TIME_TYPE": "UT",
                    "START_TIME": "'2026-04-02 02:00'",
                    "STOP_TIME": "'2026-04-10 23:00'",
                    "STEP_SIZE": "'1 h'",
                }
            )
        ],
    )

    records = fetch_orion_ephemeris()

    assert len(records) == 2


@responses.activate
def test_fetch_orion_ephemeris_parses_vector_rows(vectors_result):
    responses.add(responses.GET, DEFAULT_BASE_URL, json={"result": vectors_result})

    first = fetch_orion_ephemeris()[0]

    assert first.target_id == "-1024"
    assert first.epoch == datetime(2026, 4, 2, 2, 0, tzinfo=UTC)
    assert (first.x_km, first.y_km, first.z_km) == (10_000.0, 20_000.0, 3_000.0)
    assert first.speed_kms == pytest.approx(3.0)
    assert first.range_km == pytest.approx(22_472.20505424423)


@responses.activate
def test_fetch_orion_ephemeris_returns_empty_without_soe_markers():
    responses.add(responses.GET, DEFAULT_BASE_URL, json={"result": "No ephemeris"})

    assert fetch_orion_ephemeris() == []


@responses.activate
def test_fetch_orion_ephemeris_raises_on_horizons_error():
    responses.add(responses.GET, DEFAULT_BASE_URL, json={"error": "Bad target"})

    with pytest.raises(RuntimeError, match="Bad target"):
        fetch_orion_ephemeris()


@responses.activate
def test_fetch_orion_ephemeris_raises_on_http_error():
    responses.add(responses.GET, DEFAULT_BASE_URL, status=503)

    with pytest.raises(requests.HTTPError):
        fetch_orion_ephemeris()


@responses.activate
def test_fetch_orion_ephemeris_raises_on_dates_only_csv(dates_only_csv_result):
    responses.add(
        responses.GET, DEFAULT_BASE_URL, json={"result": dates_only_csv_result}
    )

    with pytest.raises(ValueError, match="Unrecognised line"):
        fetch_orion_ephemeris()


@responses.activate
def test_fetch_orion_ephemeris_raises_on_missing_vector_values(vectors_result):
    without_light_time_line = "\n".join(
        line for line in vectors_result.splitlines() if not line.startswith(" LT=")
    )
    responses.add(
        responses.GET, DEFAULT_BASE_URL, json={"result": without_light_time_line}
    )

    with pytest.raises(ValueError, match=r"missing \['LT', 'RG', 'RR'\]"):
        fetch_orion_ephemeris()
