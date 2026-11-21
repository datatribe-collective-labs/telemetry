"""Tests for DSN ground-station visibility."""

from datetime import UTC, datetime, timedelta

import numpy as np
import pytest
from physics_models.state_engine import dsn
from physics_models.state_engine.dsn import (
    DSN_SITES,
    DsnSite,
    compute_gmst_rad,
    compute_precession_matrix,
    compute_site_elevation_deg,
    compute_site_position,
    eme2000_to_earth_fixed,
    is_dsn_visible,
    is_line_of_sight_blocked,
    is_site_visible,
)

EPOCH = datetime(2026, 4, 5, 12, tzinfo=UTC)
SIDEREAL_DAY_S = 86_164.0905
EQUATOR_SITE = DsnSite("TEST", "Test", 0.0, 0.0, 0.0)
SEGMENT_START = np.array([0.0, 0.0, 0.0])
SEGMENT_END = np.array([100.0, 0.0, 0.0])


def _earth_fixed_to_eme2000(position: np.ndarray, t: datetime) -> np.ndarray:
    """Inverse of the rotation under test, found column by column."""
    matrix = np.column_stack([eme2000_to_earth_fixed(axis, t) for axis in np.eye(3)])
    return matrix.T @ position


def _overhead_spacecraft(site: DsnSite) -> np.ndarray:
    """EME2000 position 300,000 km straight above the site at EPOCH."""
    position, up = compute_site_position(site)
    return _earth_fixed_to_eme2000(position + 300_000.0 * up, EPOCH)


def test_compute_gmst_rad_matches_vallado_example():
    # Vallado, Fundamentals of Astrodynamics, example 3-5: 1992-08-20 12:14 UT1
    t = datetime(1992, 8, 20, 12, 14, tzinfo=UTC)
    assert np.degrees(compute_gmst_rad(t)) == pytest.approx(152.578787810, abs=1e-5)


def test_compute_gmst_rad_returns_after_one_sidereal_day():
    later = EPOCH + timedelta(seconds=SIDEREAL_DAY_S)
    assert compute_gmst_rad(later) == pytest.approx(compute_gmst_rad(EPOCH), abs=1e-4)


def test_compute_gmst_rad_reads_naive_time_as_utc():
    assert compute_gmst_rad(EPOCH.replace(tzinfo=None)) == compute_gmst_rad(EPOCH)


def test_compute_precession_matrix_is_identity_at_j2000():
    matrix = compute_precession_matrix(datetime(2000, 1, 1, 12, tzinfo=UTC))
    assert matrix == pytest.approx(np.eye(3))


def test_compute_precession_matrix_is_a_rotation():
    matrix = compute_precession_matrix(EPOCH)
    assert matrix @ matrix.T == pytest.approx(np.eye(3))
    assert np.linalg.det(matrix) == pytest.approx(1.0)


def test_compute_site_position_on_equator_is_at_semi_major_axis():
    position, up = compute_site_position(EQUATOR_SITE)
    assert position == pytest.approx(np.array([6378.137, 0.0, 0.0]))
    assert up == pytest.approx(np.array([1.0, 0.0, 0.0]))


@pytest.mark.parametrize("site", DSN_SITES, ids=lambda s: s.site)
def test_compute_site_position_has_unit_up_and_earth_radius(site):
    position, up = compute_site_position(site)
    assert np.linalg.norm(up) == pytest.approx(1.0)
    assert 6_360 < np.linalg.norm(position) < 6_380


@pytest.mark.parametrize("site", DSN_SITES, ids=lambda s: s.site)
def test_compute_site_elevation_deg_directly_overhead_is_90(site):
    spacecraft = _overhead_spacecraft(site)
    assert compute_site_elevation_deg(site, spacecraft, EPOCH) == pytest.approx(90.0, abs=1e-6)


def test_compute_site_elevation_deg_changes_as_earth_rotates():
    site = DSN_SITES[0]
    spacecraft = _overhead_spacecraft(site)
    twelve_hours_later = EPOCH + timedelta(hours=12)
    assert compute_site_elevation_deg(site, spacecraft, twelve_hours_later) < 0.0


def test_is_dsn_visible_true_when_overhead_of_a_site():
    assert is_dsn_visible(_overhead_spacecraft(DSN_SITES[1]), EPOCH) is True


def test_is_dsn_visible_false_when_every_site_is_below_cutoff():
    # Low orbit over the South Atlantic, far from all three complexes.
    fixed = 6_800.0 * np.array(
        [np.cos(np.radians(-30)) * np.cos(np.radians(-30)),
         np.cos(np.radians(-30)) * np.sin(np.radians(-30)),
         np.sin(np.radians(-30))]
    )
    assert is_dsn_visible(_earth_fixed_to_eme2000(fixed, EPOCH), EPOCH) is False


def test_is_dsn_visible_respects_the_cutoff():
    assert is_dsn_visible(_overhead_spacecraft(DSN_SITES[2]), EPOCH, cutoff_deg=90.1) is False


def test_is_dsn_visible_false_when_moon_blocks_every_site_in_view(monkeypatch):
    spacecraft = _overhead_spacecraft(DSN_SITES[1])
    # Just below Orion: every line from Earth to Orion converges through the Moon here.
    monkeypatch.setattr(dsn, "compute_moon_position_km", lambda _t: spacecraft * 0.99)
    assert is_dsn_visible(spacecraft, EPOCH) is False


def test_is_dsn_visible_true_when_moon_is_on_the_far_side_of_earth(monkeypatch):
    spacecraft = _overhead_spacecraft(DSN_SITES[1])
    monkeypatch.setattr(dsn, "compute_moon_position_km", lambda _t: -spacecraft)
    assert is_dsn_visible(spacecraft, EPOCH) is True


def test_is_site_visible_false_below_cutoff_even_with_a_clear_path(monkeypatch):
    site = DSN_SITES[0]
    spacecraft = _overhead_spacecraft(site)
    monkeypatch.setattr(dsn, "compute_moon_position_km", lambda _t: -spacecraft)
    assert is_site_visible(site, spacecraft, EPOCH, cutoff_deg=90.1) is False


def test_is_site_visible_false_when_moon_is_on_the_line(monkeypatch):
    site = DSN_SITES[0]
    spacecraft = _overhead_spacecraft(site)
    monkeypatch.setattr(dsn, "compute_moon_position_km", lambda _t: spacecraft * 0.99)
    assert is_site_visible(site, spacecraft, EPOCH) is False


@pytest.mark.parametrize(
    ("center", "blocked"),
    [
        pytest.param([50.0, 0.0, 0.0], True, id="through_the_center"),
        pytest.param([50.0, 9.9, 0.0], True, id="just_inside"),
        pytest.param([50.0, 10.0, 0.0], False, id="grazing"),
        pytest.param([50.0, 10.1, 0.0], False, id="just_outside"),
        pytest.param([120.0, 0.0, 0.0], False, id="beyond_the_end"),
        pytest.param([-20.0, 0.0, 0.0], False, id="behind_the_start"),
        pytest.param([105.0, 0.0, 0.0], True, id="sphere_contains_the_end"),
    ],
)
def test_is_line_of_sight_blocked_by_sphere_of_radius_10(center, blocked):
    assert is_line_of_sight_blocked(SEGMENT_START, SEGMENT_END, np.array(center), 10.0) is blocked
