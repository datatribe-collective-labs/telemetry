"""Tests for the radiation dose model."""

from datetime import UTC, datetime, timedelta
from itertools import pairwise
from types import SimpleNamespace

import numpy as np
import pytest
from physics_models.radiation.physics import (
    EARTH_RADIUS_KM,
    GCR_FREE_SPACE_UGY_MIN,
    INNER_BELT,
    MISSION_PEAK_PROTON_FLUX_PFU,
    MRAD_HR_PER_RAD_S,
    OUTER_BELT,
    RAD_PER_MICROGRAY,
    SEP_THRESHOLD_PFU,
    DoseProfile,
    DoseSample,
    compute_belt_dose_rate_rad_s,
    compute_blocked_sky_fraction,
    compute_gcr_dose_rate_rad_s,
    compute_instant_dose,
    compute_radiation_zone,
    is_sep_event_active,
)

START = datetime(2026, 4, 3, tzinfo=UTC)
FAR_MOON = np.array([1e9, 0.0, 0.0])


def _rad_s(ugy_min: float) -> float:
    return ugy_min * RAD_PER_MICROGRAY / 60.0


def _arc(radii_re: list[float], step_s: float = 60.0) -> SimpleNamespace:
    positions = np.column_stack(
        [np.array(radii_re) * EARTH_RADIUS_KM, np.zeros(len(radii_re)), np.zeros(len(radii_re))]
    )
    return SimpleNamespace(epochs=START.timestamp() + np.arange(len(radii_re)) * step_s, positions=positions)


@pytest.mark.parametrize(
    ("distance", "zone"),
    [
        (1.0, "LOW_EARTH"), (1.1999, "LOW_EARTH"), (1.2, "INNER_BELT"), (2.4999, "INNER_BELT"),
        (2.5, "OUTER_BELT"), (6.9999, "OUTER_BELT"), (7.0, "DEEP_SPACE"), (64.0, "DEEP_SPACE"),
    ],
)
def test_compute_radiation_zone_uses_contract_boundaries(distance, zone):
    assert compute_radiation_zone(distance) == zone


def test_compute_belt_dose_rate_peaks_at_the_inner_belt():
    assert compute_belt_dose_rate_rad_s(INNER_BELT.center_re) == pytest.approx(_rad_s(287.0), rel=1e-3)


def test_compute_belt_dose_rate_has_an_outer_belt_peak():
    assert compute_belt_dose_rate_rad_s(OUTER_BELT.center_re) == pytest.approx(_rad_s(2.7), rel=1e-3)


def test_compute_belt_dose_rate_is_negligible_in_deep_space():
    assert compute_belt_dose_rate_rad_s(30.0) < 1e-12


def test_compute_blocked_sky_fraction_is_half_at_the_surface():
    assert compute_blocked_sky_fraction(EARTH_RADIUS_KM, EARTH_RADIUS_KM) == pytest.approx(0.5)


def test_compute_blocked_sky_fraction_matches_moon_at_flyby_altitude():
    assert compute_blocked_sky_fraction(1737.4 + 6544.0, 1737.4) == pytest.approx(0.0112, abs=0.0002)


@pytest.mark.parametrize("distance", [0.0, 1.0, EARTH_RADIUS_KM])
def test_compute_blocked_sky_fraction_is_half_at_or_inside_the_surface(distance):
    assert compute_blocked_sky_fraction(distance, EARTH_RADIUS_KM) == pytest.approx(0.5)


def test_compute_gcr_rate_stays_finite_and_non_negative_at_a_body_centre():
    rate = compute_gcr_dose_rate_rad_s(np.zeros(3), np.zeros(3))
    assert rate == pytest.approx(0.0)


def test_compute_gcr_rate_is_the_measured_rate_far_from_everything():
    rate = compute_gcr_dose_rate_rad_s(np.array([-1e12, 0.0, 0.0]), FAR_MOON)
    assert rate == pytest.approx(_rad_s(GCR_FREE_SPACE_UGY_MIN), rel=1e-6)
    assert rate * 86_400 / RAD_PER_MICROGRAY == pytest.approx(400.0, rel=1e-6)


def test_compute_gcr_rate_is_reduced_near_earth():
    near = compute_gcr_dose_rate_rad_s(np.array([1.1 * EARTH_RADIUS_KM, 0.0, 0.0]), FAR_MOON)
    far = compute_gcr_dose_rate_rad_s(np.array([60 * EARTH_RADIUS_KM, 0.0, 0.0]), FAR_MOON)
    assert near < far


def test_compute_gcr_rate_is_reduced_near_the_moon():
    position = np.array([300_000.0, 0.0, 0.0])
    away = compute_gcr_dose_rate_rad_s(position, FAR_MOON)
    close = compute_gcr_dose_rate_rad_s(position, position + np.array([3_000.0, 0.0, 0.0]))
    assert close < away


def test_is_sep_event_active_is_false_for_this_flight():
    assert MISSION_PEAK_PROTON_FLUX_PFU < SEP_THRESHOLD_PFU
    assert is_sep_event_active() is False


def test_dose_sample_total_and_telemetry_units():
    sample = DoseSample(belt_rate_rad_s=1e-6, gcr_rate_rad_s=4e-6, cumulative_krad=0.0, cumulative_belt_krad=0.0)
    assert sample.total_rate_rad_s == pytest.approx(5e-6)
    assert sample.rate_mrad_hr == pytest.approx(18.0)


def test_inner_belt_peak_in_telemetry_units():
    rate = compute_belt_dose_rate_rad_s(INNER_BELT.center_re)
    assert rate * MRAD_HR_PER_RAD_S == pytest.approx(1722.0, rel=1e-3)  # 287 uGy/min


def test_dose_profile_grid_ends_exactly_at_the_arc_end():
    arc = _arc([4.0, 3.0, 2.0])
    arc.epochs = arc.epochs + np.array([0.0, 0.0, 3.7])
    profile = DoseProfile.from_ephemeris(arc)
    assert profile.seconds[0] == arc.epochs[0]
    assert profile.seconds[-1] == arc.epochs[-1]
    assert (np.diff(profile.seconds) > 0).all()
    assert np.diff(profile.seconds).max() <= 10.0


def test_dose_profile_supports_a_single_point_arc():
    profile = DoseProfile.from_ephemeris(_arc([30.0]))
    assert profile.at(START).cumulative_krad == 0.0


def test_dose_profile_cumulative_starts_at_zero():
    assert DoseProfile.from_ephemeris(_arc([1.5, 2.0, 3.0])).at(START).cumulative_krad == 0.0


def test_dose_profile_cumulative_never_decreases():
    profile = DoseProfile.from_ephemeris(_arc([4.0, 2.0, 1.2, 1.5, 3.0, 8.0]))
    totals = [profile.at(START + timedelta(seconds=s)).cumulative_krad for s in range(0, 301, 7)]
    assert all(later >= earlier for earlier, later in pairwise(totals))


def test_dose_profile_belt_share_never_exceeds_the_total():
    profile = DoseProfile.from_ephemeris(_arc([4.0, 2.0, 1.2, 1.5, 3.0, 8.0]))
    for second in range(0, 301, 13):
        sample = profile.at(START + timedelta(seconds=second))
        assert 0.0 <= sample.cumulative_belt_krad <= sample.cumulative_krad


def test_dose_profile_is_a_pure_function_of_time():
    profile = DoseProfile.from_ephemeris(_arc([4.0, 2.0, 1.5]))
    moment = START + timedelta(seconds=73)
    first = profile.at(moment)
    profile.at(START + timedelta(seconds=120))
    assert profile.at(moment) == first


def test_dose_profile_holds_the_total_after_the_arc_and_is_zero_before_it():
    profile = DoseProfile.from_ephemeris(_arc([4.0, 2.0, 1.5]))
    end = profile.at(START + timedelta(seconds=120))
    assert profile.at(START + timedelta(days=1)).cumulative_krad == end.cumulative_krad
    assert profile.at(START - timedelta(days=1)).cumulative_krad == 0.0


def test_dose_profile_reads_naive_time_as_utc():
    profile = DoseProfile.from_ephemeris(_arc([4.0, 2.0, 1.5]))
    moment = START + timedelta(seconds=40)
    assert profile.at(moment.replace(tzinfo=None)) == profile.at(moment)


def test_dose_profile_integrates_a_constant_rate():
    profile = DoseProfile.from_ephemeris(_arc([30.0] * 61), step_s=60.0)
    sample = profile.at(START + timedelta(hours=1))
    expected = sample.gcr_rate_rad_s * 3_600 / 1000.0
    assert sample.cumulative_krad == pytest.approx(expected, rel=1e-3)


def test_compute_instant_dose_has_rates_and_no_cumulative():
    sample = compute_instant_dose(np.array([1.5 * EARTH_RADIUS_KM, 0.0, 0.0]), START)
    assert sample.belt_rate_rad_s > 0.0
    assert sample.gcr_rate_rad_s > 0.0
    assert sample.cumulative_krad == 0.0
