"""Unit tests for pipelines.ingest.jpl_dsn_geometry._to_float."""

import pytest
from pipelines.ingest.jpl_dsn_geometry import _to_float


@pytest.mark.parametrize("raw, expected", [("18.312345", 18.312345), ("-0.41", -0.41)])
def test_to_float_parses_numeric_strings(raw, expected):
    assert _to_float(raw) == expected


@pytest.mark.parametrize("raw", ["n.a.", "", None])
def test_to_float_returns_none_for_unavailable_values(raw):
    assert _to_float(raw) is None
