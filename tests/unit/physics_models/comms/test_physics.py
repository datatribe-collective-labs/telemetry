"""Tests for the comms (S-band link budget) physics module."""

from math import log10

import pytest
from physics_models.comms.physics import (
    CommsModel,
    compute_eb_n0,
    compute_free_space_path_loss,
    compute_link_loss_reason,
    compute_noise_density,
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


@pytest.mark.parametrize("state", ["NOMINAL", "DEGRADED"])
@pytest.mark.parametrize("dsn_view", ["CLEAR", "MOON_BLOCKED", "OUT_OF_VIEW"])
@pytest.mark.parametrize("transmitter_on", [True, False])
def test_compute_link_loss_reason_none_while_linked(state, dsn_view, transmitter_on):
    assert compute_link_loss_reason(state, dsn_view, transmitter_on) == "NONE"


@pytest.mark.parametrize(
    ("dsn_view", "transmitter_on", "expected"),
    [
        ("MOON_BLOCKED", True, "MOON_BLOCKED"),
        ("MOON_BLOCKED", False, "MOON_BLOCKED"),
        ("OUT_OF_VIEW", True, "OUT_OF_DSN_VIEW"),
        ("OUT_OF_VIEW", False, "OUT_OF_DSN_VIEW"),
        ("CLEAR", False, "NO_POWER"),
        ("CLEAR", True, "LINK_BUDGET"),
    ],
)
def test_compute_link_loss_reason_geometry_wins(dsn_view, transmitter_on, expected):
    assert compute_link_loss_reason("NO_LINK", dsn_view, transmitter_on) == expected


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
    link = model.step(earth_distance_km=MAX_RANGE_KM)
    assert link.data_rate_kbps == 1939.4
    assert link.comm_state == "NOMINAL"
    assert link.link_margin_db == pytest.approx(model.operational_margin_db, abs=0.05)


def test_step_beyond_calibration_range_steps_rate_down(model):
    link = model.step(earth_distance_km=430_000.0)
    assert link.data_rate_kbps == 1250.0
    assert link.comm_state == "NOMINAL"


def test_step_near_earth_max_rate_and_full_quality(model):
    link = model.step(earth_distance_km=MIN_RANGE_KM)
    assert link.data_rate_kbps == 1939.4
    assert link.signal_quality == 1.0


def test_step_eirp_from_rf_power_and_antenna_gain(model):
    link = model.step(earth_distance_km=100_000.0)
    assert link.eirp_dbw == pytest.approx(10 * log10(model.max_rf_power_w) + model.tx_antenna_gain_dbi)


def test_step_link_budget_equations_hold(model):
    link = model.step(earth_distance_km=250_000.0)
    n0 = compute_noise_density(model.system_noise_temp_k)
    assert link.received_power_dbw == pytest.approx(
        link.eirp_dbw - link.free_space_path_loss_db + model.dsn_antenna_gain_dbi - model.misc_loss_db
    )
    assert link.eb_n0_db == pytest.approx(
        compute_eb_n0(link.received_power_dbw, n0, link.data_rate_kbps, model.implementation_loss_db)
    )
    assert link.link_margin_db == pytest.approx(link.eb_n0_db - model.required_eb_n0_db)


def test_step_transmitter_off_is_no_link_even_near_earth(model):
    link = model.step(earth_distance_km=MIN_RANGE_KM, transmitter_on=False)
    assert link.comm_state == "NO_LINK"
    assert link.link_loss_reason == "NO_POWER"
    assert link.data_rate_kbps == 0.0
    assert link.signal_quality == 0.0
    assert link.link_margin_db < 0.0


def test_step_no_dsn_in_view_is_no_link_even_near_earth(model):
    link = model.step(earth_distance_km=MIN_RANGE_KM, dsn_view="OUT_OF_VIEW")
    assert link.comm_state == "NO_LINK"
    assert link.link_loss_reason == "OUT_OF_DSN_VIEW"
    assert link.data_rate_kbps == 0.0
    assert link.signal_quality == 0.0
    assert link.link_margin_db < 0.0


def test_step_no_dsn_in_view_keeps_true_path_loss_and_eirp(model):
    visible = model.step(earth_distance_km=250_000.0)
    blocked = model.step(earth_distance_km=250_000.0, dsn_view="MOON_BLOCKED")
    assert blocked.free_space_path_loss_db == visible.free_space_path_loss_db
    assert blocked.eirp_dbw == visible.eirp_dbw
    assert blocked.received_power_dbw == pytest.approx(
        blocked.eirp_dbw
        - blocked.free_space_path_loss_db
        + model.dsn_antenna_gain_dbi
        - model.misc_loss_db
        - model.blocked_signal_loss_db
    )


def test_step_moon_blocked_names_the_moon(model):
    assert model.step(earth_distance_km=380_000.0, dsn_view="MOON_BLOCKED").link_loss_reason == "MOON_BLOCKED"


def test_step_out_of_range_is_a_link_budget_loss(model):
    link = model.step(earth_distance_km=50_000_000.0)
    assert link.comm_state == "NO_LINK"
    assert link.link_loss_reason == "LINK_BUDGET"


def test_step_linked_has_no_loss_reason(model):
    assert model.step(earth_distance_km=250_000.0).link_loss_reason == "NONE"


def test_step_degraded_when_lowest_rate_closes_below_operational_margin():
    model = CommsModel(required_eb_n0_db=2.0, operational_margin_db=3.0)
    # Find the range where 16 kbps has ~1.5 dB margin: start from the 16 kbps margin at
    # 410,000 km and move out by the extra path loss needed.
    at_max = model.step(earth_distance_km=MAX_RANGE_KM)
    margin_16 = at_max.link_margin_db + 10 * log10(1939.4 / 16.0)
    distance = MAX_RANGE_KM * 10 ** ((margin_16 - 1.5) / 20)
    link = model.step(earth_distance_km=distance)
    assert link.comm_state == "DEGRADED"
    assert link.data_rate_kbps == 16.0
    assert 0.0 < link.link_margin_db < 3.0
    assert link.signal_quality == pytest.approx(link.link_margin_db / 20.0)


def test_step_plasma_noise_factor_scales_signal_quality(model):
    clean = model.step(earth_distance_km=MAX_RANGE_KM)
    noisy = model.step(earth_distance_km=MAX_RANGE_KM, plasma_noise_factor=0.5)
    assert noisy.signal_quality == pytest.approx(clean.signal_quality * 0.5)


@pytest.mark.parametrize("distance_km", [MIN_RANGE_KM, 50_000.0, 200_000.0, MAX_RANGE_KM, 2_000_000.0])
@pytest.mark.parametrize("transmitter_on", [True, False])
@pytest.mark.parametrize("dsn_view", ["CLEAR", "MOON_BLOCKED", "OUT_OF_VIEW"])
def test_step_output_satisfies_contract_rules(model, distance_km, transmitter_on, dsn_view):
    link = model.step(earth_distance_km=distance_km, transmitter_on=transmitter_on, dsn_view=dsn_view)
    if dsn_view != "CLEAR" or not transmitter_on:
        assert link.comm_state == "NO_LINK"
    assert (link.link_loss_reason == "NONE") == (link.comm_state != "NO_LINK")
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
