from datetime import UTC, datetime

import pytest
from contracts import (
    SyntheticCommsOutput,
    SyntheticRadiationOutput,
    SyntheticTelemetryPacket,
)
from pydantic import ValidationError

TIMESTAMP = datetime(2026, 4, 6, 23, 0, tzinfo=UTC)
COMMS = {
    "timestamp_utc": TIMESTAMP, "eirp_dbw": 12.07, "free_space_path_loss_db": 211.0,
    "received_power_dbw": -143.0, "eb_n0_db": 5.0, "link_margin_db": 3.0,
    "data_rate_kbps": 512.0, "signal_quality": 0.15, "comm_state": "NOMINAL",
}
RADIATION = {
    "timestamp_utc": TIMESTAMP, "total_dose_rate_rad_s": 1e-7, "cumulative_dose_krad": 1e-3,
    "solar_array_degradation": 1.0, "thermal_alpha_degradation": 1.0,
    "thermal_eps_degradation": 1.0, "radiation_dose_rate_mrad_hr": 0.36,
    "sep_event_active": False,
}
PACKET = {
    "timestamp_utc": TIMESTAMP, "temp_sun_face_k": 350.0, "temp_shadow_face_k": 200.0,
    "temp_electronics_bay_k": 295.0, "heater_active": False, "thermal_state": "NOMINAL",
    "battery_voltage_v": 28.0, "battery_soc_pct": 90.0, "solar_array_power_w": 11000.0,
    "power_state": "NOMINAL", "signal_quality": 0.15, "link_margin_db": 3.0,
    "data_rate_kbps": 512.0, "comm_state": "NOMINAL", "radiation_dose_rate_mrad_hr": 0.36,
    "cumulative_dose_krad": 1e-3, "sep_event_active": False, "all_nominal": True,
}
CASES = [
    (SyntheticCommsOutput, COMMS, ["link_loss_reason"]),
    (
        SyntheticRadiationOutput,
        RADIATION,
        ["belt_dose_rate_rad_s", "gcr_dose_rate_rad_s", "cumulative_belt_dose_krad", "radiation_zone"],
    ),
    (SyntheticTelemetryPacket, PACKET, ["dsn_visibility", "link_loss_reason", "radiation_zone"]),
]


@pytest.mark.parametrize(("model", "payload", "new_fields"), CASES)
def test_synthetic_models_accept_payload_without_new_fields(model, payload, new_fields):
    parsed = model(**payload)
    assert all(getattr(parsed, field) is None for field in new_fields)


@pytest.mark.parametrize(
    "reason", ["NONE", "MOON_BLOCKED", "OUT_OF_DSN_VIEW", "NO_POWER", "LINK_BUDGET"]
)
@pytest.mark.parametrize(("model", "payload"), [(SyntheticCommsOutput, COMMS), (SyntheticTelemetryPacket, PACKET)])
def test_link_loss_reason_accepts_contract_values(model, payload, reason):
    assert model(**payload, link_loss_reason=reason).link_loss_reason == reason


@pytest.mark.parametrize(("model", "payload"), [(SyntheticCommsOutput, COMMS), (SyntheticTelemetryPacket, PACKET)])
def test_link_loss_reason_rejects_unknown_value(model, payload):
    with pytest.raises(ValidationError):
        model(**payload, link_loss_reason="SOLAR_STORM")


@pytest.mark.parametrize("zone", ["LOW_EARTH", "INNER_BELT", "OUTER_BELT", "DEEP_SPACE"])
@pytest.mark.parametrize(("model", "payload"), [(SyntheticRadiationOutput, RADIATION), (SyntheticTelemetryPacket, PACKET)])
def test_radiation_zone_accepts_contract_values(model, payload, zone):
    assert model(**payload, radiation_zone=zone).radiation_zone == zone


@pytest.mark.parametrize(("model", "payload"), [(SyntheticRadiationOutput, RADIATION), (SyntheticTelemetryPacket, PACKET)])
def test_radiation_zone_rejects_unknown_value(model, payload):
    with pytest.raises(ValidationError):
        model(**payload, radiation_zone="SLOT_REGION")
