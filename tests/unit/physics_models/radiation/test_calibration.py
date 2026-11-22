"""The dose model on the real Artemis II arc must meet the approved Artemis I targets (#19)."""

from datetime import UTC, datetime
from pathlib import Path

import numpy as np
import pytest
from physics_models.oem import load_latest_oem_from_store
from physics_models.radiation.physics import (
    EARTH_RADIUS_KM,
    RAD_PER_KRAD,
    RAD_PER_MICROGRAY,
    DoseProfile,
)

OEM_STORE = Path(__file__).parents[4] / "data" / "oem" / "all-artemis-ii-oem-files.zip"
MICROGRAY_PER_KRAD = RAD_PER_KRAD / RAD_PER_MICROGRAY


@pytest.fixture(scope="module")
def arc():
    ephemeris = load_latest_oem_from_store(OEM_STORE)
    profile = DoseProfile.from_ephemeris(ephemeris)
    positions = np.column_stack(
        [np.interp(profile.seconds, ephemeris.epochs, ephemeris.positions[:, axis]) for axis in range(3)]
    )
    radius = np.linalg.norm(positions, axis=1) / EARTH_RADIUS_KM
    deep = radius >= 7.0
    changes = np.flatnonzero(deep[1:] != deep[:-1]) + 1
    descent, exit_deep = changes[1], changes[2]  # arrive from deep space, then leave for the Moon
    perigee = descent + int(np.argmin(radius[descent:exit_deep]))
    inner_exit = perigee + int(np.argmax(radius[perigee:] >= 2.5))
    return profile, radius, perigee, inner_exit, exit_deep


def _belt_mgy(profile, first, last):
    return (profile.cumulative_belt_krad[last] - profile.cumulative_belt_krad[first]) * MICROGRAY_PER_KRAD / 1000


def test_calibration_outbound_window_is_the_perigee_before_departure(arc):
    profile, radius, perigee, _, _ = arc
    moment = datetime.fromtimestamp(profile.seconds[perigee], UTC)
    assert moment.strftime("%Y-%m-%d %H:%M") == "2026-04-02 23:49"
    assert radius[perigee] == pytest.approx(1.0285, abs=0.001)


def test_calibration_inner_belt_peak_is_within_range(arc):
    profile, _, perigee, inner_exit, _ = arc
    peak = profile.belt_rate_rad_s[perigee:inner_exit].max() * 60 / RAD_PER_MICROGRAY
    assert 144.0 <= peak <= 574.0
    assert peak == pytest.approx(287.0, rel=0.02)


def test_calibration_outbound_inner_belt_dose_is_within_range(arc):
    profile, _, perigee, inner_exit, _ = arc
    dose = _belt_mgy(profile, perigee, inner_exit)
    assert 1.57 <= dose <= 6.26
    assert dose == pytest.approx(3.13, rel=0.02)


def test_calibration_outbound_outer_belt_dose_is_within_range(arc):
    profile, _, _, inner_exit, exit_deep = arc
    dose = _belt_mgy(profile, inner_exit, exit_deep)
    assert 0.065 <= dose <= 0.26
    assert dose == pytest.approx(0.13, rel=0.05)


def test_calibration_deep_space_cosmic_ray_rate_is_within_range(arc):
    profile, radius, _, _, _ = arc
    mgy_per_day = profile.gcr_rate_rad_s[radius > 20.0] * 86_400 / RAD_PER_MICROGRAY / 1000
    assert mgy_per_day.min() >= 0.28
    assert mgy_per_day.max() <= 0.52


def test_calibration_result_does_not_depend_on_the_grid_step():
    ephemeris = load_latest_oem_from_store(OEM_STORE)
    fine = DoseProfile.from_ephemeris(ephemeris, step_s=5.0).cumulative_belt_krad[-1]
    standard = DoseProfile.from_ephemeris(ephemeris).cumulative_belt_krad[-1]
    assert standard == pytest.approx(fine, rel=0.001)
