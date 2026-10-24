"""Unit tests for pipelines.ingest.jpl_dsn_geometry.fetch_dsn_geometry.

HTTP is mocked with `responses` - no network access.
"""

import responses
from pipelines.ingest.jpl_dsn_geometry import (
    DEFAULT_BASE_URL,
    DSN_SITES,
    fetch_dsn_geometry,
)


@responses.activate
def test_fetch_dsn_geometry_queries_every_site_one_at_a_time(observer_result):
    responses.add(responses.GET, DEFAULT_BASE_URL, json={"result": observer_result})

    records = fetch_dsn_geometry()

    assert len(responses.calls) == len(DSN_SITES)
    assert [r.site for r in records[::3]] == ["DSS-14", "DSS-43", "DSS-63"]
    assert [r.complex for r in records[::3]] == ["Goldstone", "Canberra", "Madrid"]


@responses.activate
def test_fetch_dsn_geometry_limits_to_requested_sites(observer_result):
    responses.add(responses.GET, DEFAULT_BASE_URL, json={"result": observer_result})

    records = fetch_dsn_geometry(sites=[DSN_SITES["DSS-43"]])

    assert len(responses.calls) == 1
    assert {r.site for r in records} == {"DSS-43"}
