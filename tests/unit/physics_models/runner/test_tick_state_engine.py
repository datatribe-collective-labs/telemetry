"""Tests for SimulatorRunner._tick_state_engine (DSN visibility wiring)."""

from datetime import datetime, timedelta

import pytest
from physics_models import runner as runner_module

TICK = datetime.fromisoformat("2026-04-05T12:00:00Z")


@pytest.mark.parametrize("visible", [True, False])
def test_tick_state_engine_reports_dsn_visibility_for_position_and_time(
    make_runner, monkeypatch, visible
):
    calls = []

    def fake_is_dsn_visible(position, t):
        calls.append((position, t))
        return visible

    monkeypatch.setattr(runner_module, "is_dsn_visible", fake_is_dsn_visible)
    runner = make_runner(oem=False)

    state = runner._tick_state_engine(TICK, timedelta(hours=1))

    assert state.dsn_visibility is visible
    position, t = calls[0]
    assert (state.x_km, state.y_km, state.z_km) == tuple(position)
    assert t == TICK
