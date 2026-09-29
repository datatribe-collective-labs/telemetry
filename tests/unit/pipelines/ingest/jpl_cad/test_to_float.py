"""Unit tests for pipelines.ingest.jpl_cad._to_float."""

import pytest

from pipelines.ingest.jpl_cad import _to_float


def test_to_float_parses_numeric_string():
    assert _to_float("0.0421") == 0.0421


@pytest.mark.parametrize("value", [None, ""])
def test_to_float_returns_none_for_missing_value(value):
    assert _to_float(value) is None
