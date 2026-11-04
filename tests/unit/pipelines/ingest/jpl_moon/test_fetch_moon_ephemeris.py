"""Unit tests for pipelines.ingest.jpl_moon.fetch_moon_ephemeris.

HTTP is mocked with `responses` - no network access.
"""

from datetime import UTC, datetime

import pytest
import responses
from pipelines.ingest.jpl_moon import fetch_moon_ephemeris
from pipelines.ingest.jpl_orion import DEFAULT_BASE_URL
from responses import matchers


@responses.activate
def test_fetch_moon_ephemeris_requests_earth_centred_eme2000_ut_vectors(vectors_result):
    responses.add(
        responses.GET,
        DEFAULT_BASE_URL,
        json={"result": vectors_result},
        match=[
            matchers.query_param_matcher(
                {
                    "COMMAND": "'301'",
                    "EPHEM_TYPE": "VECTORS",
                    "CENTER": "'500@399'",
                    "REF_PLANE": "FRAME",
                    "TIME_TYPE": "UT",
                    "START_TIME": "'2026-04-01 22:00'",
                    "STOP_TIME": "'2026-04-11 00:00'",
                    "STEP_SIZE": "'1 h'",
                },
                strict_match=False,
            )
        ],
    )

    assert len(fetch_moon_ephemeris()) == 2


@responses.activate
def test_fetch_moon_ephemeris_parses_vector_rows(vectors_result):
    responses.add(responses.GET, DEFAULT_BASE_URL, json={"result": vectors_result})

    first = fetch_moon_ephemeris()[0]

    assert first.epoch == datetime(2026, 4, 1, 21, 30, tzinfo=UTC)
    assert (first.x_km, first.y_km, first.z_km) == (-300_000.0, 200_000.0, 100_000.0)
    assert first.range_km == pytest.approx(374_165.7386773941)
