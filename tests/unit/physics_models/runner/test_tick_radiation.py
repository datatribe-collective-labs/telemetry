"""Tests for SimulatorRunner._tick_radiation."""

from datetime import datetime, timedelta
from types import SimpleNamespace

import pytest
from physics_models.radiation import EARTH_RADIUS_KM, DoseSample

TICK = datetime.fromisoformat("2026-04-05T12:00:00Z")


def _state(distance_re: float) -> SimpleNamespace:
    distance_km = distance_re * EARTH_RADIUS_KM
    return SimpleNamespace(earth_distance_km=distance_km, x_km=distance_km, y_km=0.0, z_km=0.0)


def test_tick_radiation_outputs_are_consistent(make_runner):
    runner = make_runner(oem=False)
    runner._last_state = _state(1.5)

    output = runner._tick_radiation(TICK, timedelta(hours=1))

    assert output.total_dose_rate_rad_s == pytest.approx(output.belt_dose_rate_rad_s + output.gcr_dose_rate_rad_s)
    assert output.radiation_dose_rate_mrad_hr == pytest.approx(output.total_dose_rate_rad_s * 3_600_000)
    assert output.radiation_zone == "INNER_BELT"
    assert output.sep_event_active is False


def test_tick_radiation_degradation_is_not_modeled(make_runner):
    runner = make_runner(oem=False)
    runner._last_state = _state(30.0)

    output = runner._tick_radiation(TICK, timedelta(hours=1))

    assert output.solar_array_degradation == 1.0
    assert output.thermal_alpha_degradation == 1.0
    assert output.thermal_eps_degradation == 1.0


def test_tick_radiation_uses_the_dose_profile_when_there_is_an_arc(make_runner):
    runner = make_runner(oem=False)
    runner._last_state = _state(30.0)
    sample = DoseSample(belt_rate_rad_s=1e-7, gcr_rate_rad_s=4e-7, cumulative_krad=2e-3, cumulative_belt_krad=1e-3)
    runner.__dict__["dose_profile"] = SimpleNamespace(at=lambda _t: sample)

    output = runner._tick_radiation(TICK, timedelta(hours=1))

    assert output.total_dose_rate_rad_s == pytest.approx(5e-7)
    assert output.cumulative_dose_krad == 2e-3
    assert output.cumulative_belt_dose_krad == 1e-3
    assert output.radiation_zone == "DEEP_SPACE"
