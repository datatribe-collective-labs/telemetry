"""Tests for the comms (S-band link budget) physics module."""

from math import log10

import pytest
from physics_models.comms.physics import (
    CommsModel,
    compute_eb_n0,
    compute_free_space_path_loss,
    compute_noise_density,
    compute_rf_power,
    compute_signal_quality,
)

CONTRACT_RATES_KBPS = {0.0, 16.0, 64.0, 128.0, 256.0, 512.0, 1250.0, 1939.4}
MIN_RANGE_KM = 6_500.0  # contract 03 FSPL envelope range
MAX_RANGE_KM = 410_000.0


# ── Pure functions ──


def test_compute_free_space_path_loss_matches_contract_envelope():
    assert compute_free_space_path_loss(MIN_RANGE_KM, 2216.5e6) == pytest.approx(175.62, abs=0.01)
    assert compute_free_space_path_loss(MAX_RANGE_KM, 2216.5e6) == pytest.approx(211.62, abs=0.01)


def test_compute_free_space_path_loss_reproduces_previous_contract_envelope():
    """Same formula gives contract 03 v1.0.0's numbers with its old frequencies."""
    assert compute_free_space_path_loss(MIN_RANGE_KM, 2.27e9) == pytest.approx(175.83, abs=0.01)
    assert compute_free_space_path_loss(MAX_RANGE_KM, 2.30e9) == pytest.approx(211.94, abs=0.01)


def test_compute_free_space_path_loss_doubling_distance_adds_6_db():
    near = compute_free_space_path_loss(100_000.0, 2216.5e6)
    far = compute_free_space_path_loss(200_000.0, 2216.5e6)
    assert far - near == pytest.approx(20 * log10(2))


def test_compute_noise_density_at_290_k_is_textbook_value():
    assert compute_noise_density(290.0) == pytest.approx(-203.98, abs=0.01)


def test_compute_eb_n0_subtracts_noise_rate_and_losses():
    # Pr -140 dBW, N0 -210 dBW/Hz -> C/N0 70 dB-Hz; 1000 kbps = 60 dB-Hz; 1 dB loss
    assert compute_eb_n0(-140.0, -210.0, 1000.0, 1.0) == pytest.approx(9.0)


def test_compute_rf_power_full_when_headroom_covers_draw():
    assert compute_rf_power(10.0, 150.0, 150.0) == 10.0
    assert compute_rf_power(10.0, 5_000.0, 150.0) == 10.0


def test_compute_rf_power_scales_below_draw():
    assert compute_rf_power(10.0, 75.0, 150.0) == pytest.approx(5.0)


def test_compute_rf_power_zero_without_headroom():
    assert compute_rf_power(10.0, 0.0, 150.0) == 0.0
    assert compute_rf_power(10.0, -5.0, 150.0) == 0.0


def test_compute_signal_quality_normalises_and_clamps():
    assert compute_signal_quality(0.0) == 0.0
    assert compute_signal_quality(10.0) == pytest.approx(0.5)
    assert compute_signal_quality(35.0) == 1.0
    assert compute_signal_quality(-3.0) == 0.0


# ── CommsModel.step ──


@pytest.fixture
def model():
    return CommsModel()


def test_step_calibration_closes_max_rate_with_operational_margin_at_lunar_range(model):
    """EIRP is calibrated to NASA's "up to ~2 Mb/s from lunar ranges"."""
    link = model.step(earth_distance_km=MAX_RANGE_KM, available_power_w=None)
    assert link.data_rate_kbps == 1939.4
    assert link.comm_state == "NOMINAL"
    assert link.link_margin_db == pytest.approx(model.operational_margin_db, abs=0.05)


def test_step_beyond_calibration_range_steps_rate_down(model):
    link = model.step(earth_distance_km=430_000.0, available_power_w=None)
    assert link.data_rate_kbps == 1250.0
    assert link.comm_state == "NOMINAL"


def test_step_near_earth_max_rate_and_full_quality(model):
    link = model.step(earth_distance_km=MIN_RANGE_KM, available_power_w=1_000.0)
    assert link.data_rate_kbps == 1939.4
    assert link.signal_quality == 1.0


def test_step_eirp_from_rf_power_and_antenna_gain(model):
    link = model.step(earth_distance_km=100_000.0, available_power_w=75.0)  # half power
    assert link.eirp_dbw == pytest.approx(10 * log10(5.0) + model.tx_antenna_gain_dbi)


def test_step_link_budget_equations_hold(model):
    link = model.step(earth_distance_km=250_000.0, available_power_w=None)
    n0 = compute_noise_density(model.system_noise_temp_k)
    assert link.received_power_dbw == pytest.approx(
        link.eirp_dbw - link.free_space_path_loss_db + model.dsn_antenna_gain_dbi - model.misc_loss_db
    )
    assert link.eb_n0_db == pytest.approx(
        compute_eb_n0(link.received_power_dbw, n0, link.data_rate_kbps, model.implementation_loss_db)
    )
    assert link.link_margin_db == pytest.approx(link.eb_n0_db - model.required_eb_n0_db)


def test_step_partial_headroom_lowers_rate(model):
    full = model.step(earth_distance_km=MAX_RANGE_KM, available_power_w=150.0)
    reduced = model.step(earth_distance_km=MAX_RANGE_KM, available_power_w=15.0)  # -10 dB
    assert reduced.data_rate_kbps < full.data_rate_kbps
    assert reduced.comm_state == "NOMINAL"


def test_step_no_headroom_is_no_link_even_near_earth(model):
    link = model.step(earth_distance_km=MIN_RANGE_KM, available_power_w=0.0)
    assert link.comm_state == "NO_LINK"
    assert link.data_rate_kbps == 0.0
    assert link.signal_quality == 0.0
    assert link.link_margin_db < 0.0


def test_step_no_dsn_in_view_is_no_link_even_near_earth(model):
    link = model.step(earth_distance_km=MIN_RANGE_KM, available_power_w=1_000.0, dsn_visible=False)
    assert link.comm_state == "NO_LINK"
    assert link.data_rate_kbps == 0.0
    assert link.signal_quality == 0.0
    assert link.link_margin_db < 0.0


def test_step_no_dsn_in_view_keeps_true_path_loss_and_eirp(model):
    visible = model.step(earth_distance_km=250_000.0, available_power_w=1_000.0)
    blocked = model.step(earth_distance_km=250_000.0, available_power_w=1_000.0, dsn_visible=False)
    assert blocked.free_space_path_loss_db == visible.free_space_path_loss_db
    assert blocked.eirp_dbw == visible.eirp_dbw
    assert blocked.received_power_dbw == pytest.approx(
        blocked.eirp_dbw
        - blocked.free_space_path_loss_db
        + model.dsn_antenna_gain_dbi
        - model.misc_loss_db
        - model.blocked_signal_loss_db
    )


def test_step_degraded_when_lowest_rate_closes_below_operational_margin():
    model = CommsModel(required_eb_n0_db=2.0, operational_margin_db=3.0)
    # Find the range where 16 kbps has ~1.5 dB margin: start from the 16 kbps margin at
    # 410,000 km and move out by the extra path loss needed.
    at_max = model.step(earth_distance_km=MAX_RANGE_KM, available_power_w=None)
    margin_16 = at_max.link_margin_db + 10 * log10(1939.4 / 16.0)
    distance = MAX_RANGE_KM * 10 ** ((margin_16 - 1.5) / 20)
    link = model.step(earth_distance_km=distance, available_power_w=None)
    assert link.comm_state == "DEGRADED"
    assert link.data_rate_kbps == 16.0
    assert 0.0 < link.link_margin_db < 3.0
    assert link.signal_quality == pytest.approx(link.link_margin_db / 20.0)


def test_step_plasma_noise_factor_scales_signal_quality(model):
    clean = model.step(earth_distance_km=MAX_RANGE_KM, available_power_w=None)
    noisy = model.step(earth_distance_km=MAX_RANGE_KM, available_power_w=None, plasma_noise_factor=0.5)
    assert noisy.signal_quality == pytest.approx(clean.signal_quality * 0.5)


@pytest.mark.parametrize("distance_km", [MIN_RANGE_KM, 50_000.0, 200_000.0, MAX_RANGE_KM, 2_000_000.0])
@pytest.mark.parametrize("available_w", [None, 0.0, 1.0, 40.0, 150.0, 10_000.0])
@pytest.mark.parametrize("dsn_visible", [True, False])
def test_step_output_satisfies_contract_rules(model, distance_km, available_w, dsn_visible):
    link = model.step(
        earth_distance_km=distance_km, available_power_w=available_w, dsn_visible=dsn_visible
    )
    if not dsn_visible:
        assert link.comm_state == "NO_LINK"
    assert link.data_rate_kbps in CONTRACT_RATES_KBPS
    assert 0.0 <= link.signal_quality <= 1.0
    assert link.link_margin_db == pytest.approx(link.eb_n0_db - model.required_eb_n0_db)
    if link.comm_state == "NO_LINK":
        assert link.data_rate_kbps == 0.0
        assert link.signal_quality == 0.0
        assert link.link_margin_db < 0.0
    else:
        assert link.data_rate_kbps > 0.0
        assert link.signal_quality > 0.0
