"""Unit tests for pipelines.ingest.jpl_dsn_geometry.is_visible."""

import pytest
from pipelines.ingest.jpl_dsn_geometry import ELEVATION_CUTOFF_DEG, is_visible


def test_is_visible_true_at_exactly_the_cutoff():
    assert is_visible(ELEVATION_CUTOFF_DEG) is True


@pytest.mark.parametrize("elevation", [9.999, 0.0, -45.0])
def test_is_visible_false_below_the_cutoff(elevation):
    assert is_visible(elevation) is False


def test_is_visible_none_when_elevation_unknown():
    assert is_visible(None) is None
