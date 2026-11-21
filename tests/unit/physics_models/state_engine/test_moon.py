"""Tests for the bundled Moon ephemeris."""

from datetime import UTC, datetime, timedelta

import numpy as np
import pytest
from physics_models.state_engine.moon import compute_moon_position_km

FIRST_EPOCH = datetime(2026, 4, 1, 22, 0, tzinfo=UTC)
FIRST_POSITION = np.array([-386861.253, -53773.826, -43562.272])
SECOND_POSITION = np.array([-386779.772, -54301.666, -43842.912])
LAST_EPOCH = datetime(2026, 4, 11, 0, 0, tzinfo=UTC)


def test_compute_moon_position_km_returns_table_value_at_an_epoch():
    assert compute_moon_position_km(FIRST_EPOCH) == pytest.approx(FIRST_POSITION)


def test_compute_moon_position_km_interpolates_between_epochs():
    midpoint = FIRST_EPOCH + timedelta(minutes=5)
    assert compute_moon_position_km(midpoint) == pytest.approx((FIRST_POSITION + SECOND_POSITION) / 2)


def test_compute_moon_position_km_reads_naive_time_as_utc():
    assert compute_moon_position_km(FIRST_EPOCH.replace(tzinfo=None)) == pytest.approx(FIRST_POSITION)


def test_compute_moon_position_km_uses_nearest_end_outside_the_table():
    before = compute_moon_position_km(FIRST_EPOCH - timedelta(days=1))
    after = compute_moon_position_km(LAST_EPOCH + timedelta(days=1))
    assert before == pytest.approx(FIRST_POSITION)
    assert after == pytest.approx(compute_moon_position_km(LAST_EPOCH))


@pytest.mark.parametrize("hours", range(0, 219, 24))
def test_compute_moon_position_km_stays_at_lunar_distance(hours):
    position = compute_moon_position_km(FIRST_EPOCH + timedelta(hours=hours))
    assert 350_000 < np.linalg.norm(position) < 410_000
