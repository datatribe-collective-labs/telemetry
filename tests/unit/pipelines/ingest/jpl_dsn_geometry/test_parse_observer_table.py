"""Unit tests for pipelines.ingest.jpl_dsn_geometry.parse_observer_table."""

from datetime import UTC, datetime

import pytest
from pipelines.ingest.jpl_dsn_geometry import KM_PER_AU, parse_observer_table


def test_parse_observer_table_converts_units_and_flags_visibility(observer_result, goldstone):
    first, second, _ = parse_observer_table(observer_result, "-1024", goldstone)

    assert first.site == "DSS-14"
    assert first.complex == "Goldstone"
    assert first.epoch == datetime(2026, 4, 5, 9, 0, tzinfo=UTC)
    assert first.azimuth_deg == 112.40281
    assert first.elevation_deg == 18.312345
    assert first.range_km == pytest.approx(0.0022054 * KM_PER_AU)
    assert first.range_rate_kms == -0.4123456
    assert first.light_time_s == pytest.approx(0.0183483 * 60)
    assert first.visible is True
    assert second.visible is False  # 8.4 deg, below the 10 deg cutoff


def test_parse_observer_table_maps_unavailable_values_to_none(observer_result, goldstone):
    last = parse_observer_table(observer_result, "-1024", goldstone)[-1]

    assert last.epoch == datetime(2026, 4, 5, 18, 0, tzinfo=UTC)
    assert last.elevation_deg is None
    assert last.range_km is None
    assert last.light_time_s is None
    assert last.visible is None


def test_parse_observer_table_returns_empty_list_without_data_markers(goldstone):
    assert parse_observer_table("No ephemeris for target", "-1024", goldstone) == []


def test_parse_observer_table_raises_when_a_column_is_missing(observer_result, goldstone):
    without_light_time = observer_result.replace("1-way_down_LT", "something_else")

    with pytest.raises(ValueError, match="1-way_down_LT"):
        parse_observer_table(without_light_time, "-1024", goldstone)
