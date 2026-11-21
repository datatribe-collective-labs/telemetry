"""Tests for SimulatorRunner._build_ml_features (DSN visibility wiring)."""

from datetime import datetime
from types import SimpleNamespace

import pytest

TICK = datetime.fromisoformat("2026-04-05T12:00:00Z")


@pytest.mark.parametrize(("visible", "expected"), [(True, 1.0), (False, 0.0)])
def test_build_ml_features_dsn_visible_follows_state(make_runner, visible, expected):
    runner = make_runner(oem=False)
    runner._last_state = SimpleNamespace(dsn_visibility=visible)
    packet = SimpleNamespace(timestamp_utc=TICK, signal_quality=0.5)

    features = runner._build_ml_features(packet)

    assert features.dsn_visible == expected
