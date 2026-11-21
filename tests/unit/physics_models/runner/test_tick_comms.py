"""Tests for SimulatorRunner._tick_comms (DSN visibility wiring)."""

from datetime import datetime, timedelta
from types import SimpleNamespace

TICK = datetime.fromisoformat("2026-04-05T12:00:00Z")


def test_tick_comms_no_link_when_no_dsn_in_view(make_runner):
    runner = make_runner(oem=False)
    runner._last_state = SimpleNamespace(earth_distance_km=250_000.0, dsn_visibility=False)

    comms = runner._tick_comms(TICK, timedelta(hours=1))

    assert comms.comm_state == "NO_LINK"
    assert comms.data_rate_kbps == 0.0


def test_tick_comms_links_when_dsn_in_view(make_runner):
    runner = make_runner(oem=False)
    runner._last_state = SimpleNamespace(earth_distance_km=250_000.0, dsn_visibility=True)

    comms = runner._tick_comms(TICK, timedelta(hours=1))

    assert comms.comm_state == "NOMINAL"
    assert comms.data_rate_kbps > 0.0
