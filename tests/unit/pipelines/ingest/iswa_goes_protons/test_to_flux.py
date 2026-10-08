"""Unit tests for pipelines.ingest.iswa_goes_protons._to_flux."""

import pytest
from pipelines.ingest.iswa_goes_protons import _to_flux


def test_to_flux_returns_float_for_real_value():
    assert _to_flux(0.34, "-100000") == 0.34


def test_to_flux_keeps_zero_flux():
    assert _to_flux(0, "-100000") == 0.0


@pytest.mark.parametrize(("value", "fill"), [(-100000, "-100000"), ("null", "null"), (None, "null")])
def test_to_flux_returns_none_for_fill_value(value, fill):
    assert _to_flux(value, fill) is None
