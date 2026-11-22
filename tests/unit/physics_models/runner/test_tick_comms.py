"""Tests for SimulatorRunner._tick_comms (DSN view and battery-state wiring)."""

from datetime import datetime, timedelta
from types import SimpleNamespace

import pytest
from physics_models import runner as runner_module

TICK = datetime.fromisoformat("2026-04-05T12:00:00Z")


def _state(visible: bool) -> SimpleNamespace:
    return SimpleNamespace(
        earth_distance_km=250_000.0, dsn_visibility=visible, x_km=250_000.0, y_km=0.0, z_km=0.0
    )


@pytest.mark.parametrize(
    ("dsn_view", "reason"), [("OUT_OF_VIEW", "OUT_OF_DSN_VIEW"), ("MOON_BLOCKED", "MOON_BLOCKED")]
)
def test_tick_comms_no_link_names_the_geometry(make_runner, monkeypatch, dsn_view, reason):
    monkeypatch.setattr(runner_module, "compute_dsn_view", lambda _position, _t: dsn_view)
    runner = make_runner(oem=False)
    runner._last_state = _state(visible=False)

    comms = runner._tick_comms(TICK, timedelta(hours=1))

    assert comms.comm_state == "NO_LINK"
    assert comms.data_rate_kbps == 0.0
    assert comms.link_loss_reason == reason


def test_tick_comms_links_when_dsn_in_view(make_runner):
    runner = make_runner(oem=False)
    runner._last_state = _state(visible=True)

    comms = runner._tick_comms(TICK, timedelta(hours=1))

    assert comms.comm_state == "NOMINAL"
    assert comms.data_rate_kbps > 0.0
    assert comms.link_loss_reason == "NONE"


def test_tick_comms_stays_linked_with_no_solar_headroom(make_runner):
    runner = make_runner(oem=False)
    runner._last_state = _state(visible=True)
    runner.cross_model.available_power_w = 0.0
    runner.cross_model.power_state = "BATTERY_DISCHARGE"

    assert runner._tick_comms(TICK, timedelta(hours=1)).comm_state == "NOMINAL"


def test_tick_comms_transmitter_off_when_previous_tick_was_critical(make_runner):
    runner = make_runner(oem=False)
    runner._last_state = _state(visible=True)
    runner.cross_model.power_state = "CRITICAL"

    comms = runner._tick_comms(TICK, timedelta(hours=1))

    assert comms.comm_state == "NO_LINK"
    assert comms.link_loss_reason == "NO_POWER"
