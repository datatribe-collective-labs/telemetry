"""Unit tests for pipelines.ingest.iswa_goes_protons.GoesProtonFlux.from_api_row."""

from datetime import UTC, datetime

from pipelines.ingest.iswa_goes_protons import GoesProtonFlux


def _row_and_fills(hapi_response, index):
    names = [p["name"] for p in hapi_response["parameters"]]
    fills = {p["name"]: p.get("fill") for p in hapi_response["parameters"]}
    return dict(zip(names, hapi_response["data"][index])), fills


def test_goes_proton_flux_from_api_row_maps_all_channels(hapi_response, make_goes_proton_flux):
    row, fills = _row_and_fills(hapi_response, 0)

    assert GoesProtonFlux.from_api_row(row, fills) == make_goes_proton_flux()


def test_goes_proton_flux_from_api_row_maps_fill_values_to_none(hapi_response):
    row, fills = _row_and_fills(hapi_response, 1)

    record = GoesProtonFlux.from_api_row(row, fills)

    assert record.time == datetime(2026, 4, 1, 22, 5, tzinfo=UTC)
    assert record.p1_pfu is None  # numeric fill -100000
    assert record.p60_pfu is None  # string fill "null"
    assert record.p500_pfu is None  # JSON null
    assert record.proton_satellite is None  # satellite fill "-1"
    assert record.p10_pfu == 0.33
