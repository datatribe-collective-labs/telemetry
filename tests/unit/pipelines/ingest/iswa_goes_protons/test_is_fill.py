"""Unit tests for pipelines.ingest.iswa_goes_protons._is_fill."""

import pytest
from pipelines.ingest.iswa_goes_protons import _is_fill


@pytest.mark.parametrize(
    ("value", "fill"),
    [
        (-100000, "-100000"),
        (-100000.0, "-100000"),
        ("-100000", "-100000"),
        ("null", "null"),
        ("-1", "-1"),
        (None, "-100000"),
        ("", None),
    ],
)
def test_is_fill_detects_fill_values(value, fill):
    assert _is_fill(value, fill) is True


@pytest.mark.parametrize(
    ("value", "fill"),
    [
        (0.34, "-100000"),
        (0.0, "-100000"),
        (0.34, "null"),
        ("GOES-18", "-1"),
        (0.34, None),
    ],
)
def test_is_fill_keeps_real_values(value, fill):
    assert _is_fill(value, fill) is False
