"""Tests for compute_moon_positions_km."""

from datetime import UTC, datetime, timedelta

import numpy as np
import pytest
from physics_models.state_engine.moon import (
    compute_moon_position_km,
    compute_moon_positions_km,
)


def test_compute_moon_positions_km_matches_the_single_time_function():
    moments = [datetime(2026, 4, 6, tzinfo=UTC) + timedelta(minutes=7 * i) for i in range(5)]

    positions = compute_moon_positions_km(np.array([m.timestamp() for m in moments]))

    for moment, position in zip(moments, positions, strict=True):
        assert position == pytest.approx(compute_moon_position_km(moment))


def test_compute_moon_positions_km_returns_one_row_per_time():
    start = datetime(2026, 4, 6, tzinfo=UTC).timestamp()
    assert compute_moon_positions_km(np.array([start, start + 60.0, start + 120.0])).shape == (3, 3)
