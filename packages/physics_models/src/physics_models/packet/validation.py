"""Check one tick's outputs against the contract rules before anything is published.

An invalid tick publishes nothing. This covers bad data only: a Kafka failure part way
through sending a valid tick can still deliver some of its messages.

Cumulative dose is not compared between ticks here: the dose profile is built so it
never decreases along a replay.
"""

from dataclasses import dataclass, fields
from math import isclose, isfinite

from contracts import (
    SyntheticCommsOutput,
    SyntheticMLFeatureVector,
    SyntheticPowerOutput,
    SyntheticRadiationOutput,
    SyntheticStateSnapshot,
    SyntheticTelemetryPacket,
    SyntheticThermalOutput,
)

from physics_models.radiation import MRAD_HR_PER_RAD_S


@dataclass(frozen=True)
class TickOutputs:
    """Everything one tick will publish, apart from the bus message derived from it."""

    state: SyntheticStateSnapshot
    thermal: SyntheticThermalOutput
    power: SyntheticPowerOutput
    comms: SyntheticCommsOutput
    radiation: SyntheticRadiationOutput
    packet: SyntheticTelemetryPacket
    ml_features: SyntheticMLFeatureVector


def _check_common(outputs: TickOutputs) -> list[str]:
    errors = []
    expected_time = outputs.state.timestamp_utc
    for item in fields(outputs):
        message = getattr(outputs, item.name)
        if message.timestamp_utc != expected_time:
            errors.append(f"{item.name}.timestamp_utc differs from the state timestamp")
        for name, value in message.model_dump().items():
            if isinstance(value, float) and not isfinite(value):
                errors.append(f"{item.name}.{name} is not finite")
    return errors


def _check_state(state: SyntheticStateSnapshot) -> list[str]:
    errors = []
    if not 0.0 <= state.eclipse_fraction <= 1.0:
        errors.append("state.eclipse_fraction is outside [0, 1]")
    if state.earth_distance_km <= 0.0:
        errors.append("state.earth_distance_km must be > 0")
    return errors


def _check_thermal(thermal: SyntheticThermalOutput) -> list[str]:
    temperatures = ("temp_sun_face_k", "temp_shadow_face_k", "temp_electronics_bay_k")
    return [f"thermal.{name} must be > 0 K" for name in temperatures if getattr(thermal, name) <= 0.0]


def _expected_power_band(soc_pct: float) -> set[str]:
    if soc_pct <= 10.0:
        return {"CRITICAL"}
    if soc_pct <= 20.0:
        return {"LOW_POWER_MODE"}
    return {"NOMINAL", "BATTERY_DISCHARGE"}


def _check_power(power: SyntheticPowerOutput, state: SyntheticStateSnapshot) -> list[str]:
    errors = []
    if not 0.0 <= power.battery_soc_pct <= 100.0:
        errors.append("power.battery_soc_pct is outside [0, 100]")
    if power.solar_array_power_w < 0.0:
        errors.append("power.solar_array_power_w must be >= 0")
    if power.available_power_w < 0.0:
        errors.append("power.available_power_w must be >= 0")
    if power.battery_voltage_v <= 0.0:
        errors.append("power.battery_voltage_v must be > 0")
    if state.eclipse_state == "UMBRA" and power.solar_array_power_w != 0.0:
        errors.append("power.solar_array_power_w must be 0 in UMBRA")
    if power.power_state not in _expected_power_band(power.battery_soc_pct):
        errors.append("power.power_state does not match battery_soc_pct")
    return errors


def _check_comms(comms: SyntheticCommsOutput, state: SyntheticStateSnapshot) -> list[str]:
    errors = []
    if not 0.0 <= comms.signal_quality <= 1.0:
        errors.append("comms.signal_quality is outside [0, 1]")
    if comms.link_loss_reason is None:
        errors.append("comms.link_loss_reason is missing")
    elif (comms.link_loss_reason == "NONE") != (comms.comm_state != "NO_LINK"):
        errors.append("comms.link_loss_reason does not match comm_state")
    if not state.dsn_visibility and comms.comm_state != "NO_LINK":
        errors.append("comms has a link while no DSN complex has a clear view")
    if comms.comm_state == "NO_LINK":
        if comms.data_rate_kbps != 0.0 or comms.signal_quality != 0.0:
            errors.append("comms NO_LINK must have zero data rate and signal quality")
        if comms.link_margin_db >= 0.0:
            errors.append("comms NO_LINK must have a negative link margin")
    elif comms.data_rate_kbps <= 0.0 or comms.signal_quality <= 0.0:
        errors.append("comms link must have a positive data rate and signal quality")
    return errors


def _check_radiation(radiation: SyntheticRadiationOutput) -> list[str]:
    required = (
        "belt_dose_rate_rad_s",
        "gcr_dose_rate_rad_s",
        "cumulative_belt_dose_krad",
        "radiation_zone",
    )
    missing = [f"radiation.{name} is missing" for name in required if getattr(radiation, name) is None]
    if missing:
        return missing
    names = (
        "total_dose_rate_rad_s",
        "cumulative_dose_krad",
        "radiation_dose_rate_mrad_hr",
        "belt_dose_rate_rad_s",
        "gcr_dose_rate_rad_s",
        "cumulative_belt_dose_krad",
    )
    errors = [
        f"radiation.{name} must be >= 0"
        for name in names
        if (value := getattr(radiation, name)) is not None and value < 0.0
    ]
    if not 0.0 < radiation.solar_array_degradation <= 1.0:
        errors.append("radiation.solar_array_degradation is outside (0, 1]")
    total = radiation.total_dose_rate_rad_s
    if not isclose(total, radiation.belt_dose_rate_rad_s + radiation.gcr_dose_rate_rad_s, rel_tol=1e-9):
        errors.append("radiation.total_dose_rate_rad_s must equal belt plus cosmic-ray rates")
    if not isclose(radiation.radiation_dose_rate_mrad_hr, total * MRAD_HR_PER_RAD_S, rel_tol=1e-9):
        errors.append("radiation.radiation_dose_rate_mrad_hr must equal total rate x 3,600,000")
    if radiation.cumulative_belt_dose_krad > radiation.cumulative_dose_krad:
        errors.append("radiation.cumulative_belt_dose_krad exceeds cumulative_dose_krad")
    return errors


def _check_packet(outputs: TickOutputs) -> list[str]:
    packet = outputs.packet
    expected = (
        outputs.thermal.thermal_state == "NOMINAL"
        and outputs.power.power_state == "NOMINAL"
        and outputs.comms.comm_state == "NOMINAL"
    )
    errors = []
    if packet.all_nominal != expected:
        errors.append("packet.all_nominal does not match the subsystem states")
    if packet.link_loss_reason != outputs.comms.link_loss_reason:
        errors.append("packet.link_loss_reason differs from comms")
    if packet.dsn_visibility != outputs.state.dsn_visibility:
        errors.append("packet.dsn_visibility differs from state")
    return errors


def validate_tick(outputs: TickOutputs) -> list[str]:
    """Every contract violation in this tick; an empty list means it may be published."""
    return [
        *_check_common(outputs),
        *_check_state(outputs.state),
        *_check_thermal(outputs.thermal),
        *_check_power(outputs.power, outputs.state),
        *_check_comms(outputs.comms, outputs.state),
        *_check_radiation(outputs.radiation),
        *_check_packet(outputs),
    ]
