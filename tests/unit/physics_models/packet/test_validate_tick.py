"""Tests for validate_tick."""

from dataclasses import replace
from datetime import timedelta

import pytest
from physics_models.packet import validate_tick

NO_LINK = {
    "comm_state": "NO_LINK", "link_loss_reason": "OUT_OF_DSN_VIEW", "data_rate_kbps": 0.0,
    "signal_quality": 0.0, "link_margin_db": -190.0,
}


def test_validate_tick_accepts_a_valid_tick(make_outputs):
    assert validate_tick(make_outputs()) == []


def test_validate_tick_accepts_a_valid_no_link_tick(make_outputs):
    assert validate_tick(make_outputs(state={"dsn_visibility": False}, comms=NO_LINK)) == []


@pytest.mark.parametrize("value", [float("nan"), float("inf"), float("-inf")])
@pytest.mark.parametrize(
    ("model", "field"),
    [
        ("state", "x_km"), ("thermal", "temp_sun_face_k"), ("power", "battery_voltage_v"),
        ("comms", "eirp_dbw"), ("radiation", "total_dose_rate_rad_s"),
    ],
)
def test_validate_tick_rejects_non_finite_values(make_outputs, model, field, value):
    errors = validate_tick(make_outputs(**{model: {field: value}}))
    assert f"{model}.{field} is not finite" in errors


def test_validate_tick_rejects_non_finite_ml_feature(make_outputs):
    outputs = make_outputs()
    bad = replace(outputs, ml_features=outputs.ml_features.model_copy(update={"soc_norm": float("nan")}))
    assert "ml_features.soc_norm is not finite" in validate_tick(bad)


def test_validate_tick_rejects_mismatched_timestamp(make_outputs):
    outputs = make_outputs()
    later = outputs.power.timestamp_utc + timedelta(seconds=60)
    bad = replace(outputs, power=outputs.power.model_copy(update={"timestamp_utc": later}))
    assert "power.timestamp_utc differs from the state timestamp" in validate_tick(bad)


@pytest.mark.parametrize(
    ("override", "message"),
    [
        ({"state": {"eclipse_fraction": 1.5}}, "state.eclipse_fraction is outside [0, 1]"),
        ({"state": {"earth_distance_km": 0.0}}, "state.earth_distance_km must be > 0"),
        ({"thermal": {"temp_electronics_bay_k": 0.0}}, "thermal.temp_electronics_bay_k must be > 0 K"),
        ({"power": {"battery_soc_pct": 101.0}}, "power.battery_soc_pct is outside [0, 100]"),
        ({"power": {"solar_array_power_w": -1.0}}, "power.solar_array_power_w must be >= 0"),
        ({"power": {"available_power_w": -1.0}}, "power.available_power_w must be >= 0"),
        ({"power": {"battery_voltage_v": 0.0}}, "power.battery_voltage_v must be > 0"),
        ({"state": {"eclipse_state": "UMBRA", "eclipse_fraction": 1.0}}, "power.solar_array_power_w must be 0 in UMBRA"),
        ({"comms": {"signal_quality": 1.5}}, "comms.signal_quality is outside [0, 1]"),
        ({"comms": {"link_loss_reason": None}}, "comms.link_loss_reason is missing"),
        ({"comms": {"link_loss_reason": "NO_POWER"}}, "comms.link_loss_reason does not match comm_state"),
        ({"state": {"dsn_visibility": False}}, "comms has a link while no DSN complex has a clear view"),
        ({"comms": {**NO_LINK, "data_rate_kbps": 16.0}}, "comms NO_LINK must have zero data rate and signal quality"),
        ({"comms": {**NO_LINK, "link_margin_db": 0.0}}, "comms NO_LINK must have a negative link margin"),
        ({"comms": {"data_rate_kbps": 0.0}}, "comms link must have a positive data rate and signal quality"),
        ({"radiation": {"cumulative_dose_krad": -1.0}}, "radiation.cumulative_dose_krad must be >= 0"),
        ({"radiation": {"belt_dose_rate_rad_s": -1.0}}, "radiation.belt_dose_rate_rad_s must be >= 0"),
        ({"radiation": {"solar_array_degradation": 0.0}}, "radiation.solar_array_degradation is outside (0, 1]"),
        ({"radiation": {"belt_dose_rate_rad_s": None}}, "radiation.belt_dose_rate_rad_s is missing"),
        ({"radiation": {"gcr_dose_rate_rad_s": None}}, "radiation.gcr_dose_rate_rad_s is missing"),
        ({"radiation": {"cumulative_belt_dose_krad": None}}, "radiation.cumulative_belt_dose_krad is missing"),
        ({"radiation": {"radiation_zone": None}}, "radiation.radiation_zone is missing"),
        ({"radiation": {"total_dose_rate_rad_s": 6e-6}}, "radiation.total_dose_rate_rad_s must equal belt plus cosmic-ray rates"),
        ({"radiation": {"radiation_dose_rate_mrad_hr": 19.0}}, "radiation.radiation_dose_rate_mrad_hr must equal total rate x 3,600,000"),
        ({"radiation": {"cumulative_belt_dose_krad": 2e-3}}, "radiation.cumulative_belt_dose_krad exceeds cumulative_dose_krad"),
    ],
)
def test_validate_tick_rejects_contract_violations(make_outputs, override, message):
    assert message in validate_tick(make_outputs(**override))


@pytest.mark.parametrize(
    ("soc", "state", "valid"),
    [
        (10.0, "CRITICAL", True), (10.01, "LOW_POWER_MODE", True), (20.0, "LOW_POWER_MODE", True),
        (20.01, "NOMINAL", True), (20.01, "BATTERY_DISCHARGE", True), (5.0, "NOMINAL", False),
        (15.0, "CRITICAL", False), (50.0, "LOW_POWER_MODE", False),
    ],
)
def test_validate_tick_power_state_follows_battery_band(make_outputs, soc, state, valid):
    errors = validate_tick(make_outputs(power={"battery_soc_pct": soc, "power_state": state}))
    assert ("power.power_state does not match battery_soc_pct" not in errors) is valid


@pytest.mark.parametrize(
    ("update", "message"),
    [
        ({"all_nominal": False}, "packet.all_nominal does not match the subsystem states"),
        ({"link_loss_reason": "NO_POWER"}, "packet.link_loss_reason differs from comms"),
        ({"dsn_visibility": False}, "packet.dsn_visibility differs from state"),
    ],
)
def test_validate_tick_rejects_packet_that_disagrees_with_sources(make_outputs, update, message):
    outputs = make_outputs()
    bad = replace(outputs, packet=outputs.packet.model_copy(update=update))
    assert message in validate_tick(bad)
