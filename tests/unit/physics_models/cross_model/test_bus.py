"""Tests for the cross-model coupling bus."""

from datetime import UTC, datetime

from contracts import (
    SyntheticCommsOutput,
    SyntheticPowerOutput,
    SyntheticRadiationOutput,
    SyntheticThermalOutput,
)
from physics_models.cross_model import CrossModelBus

T0 = datetime(2026, 4, 2, 2, 0, tzinfo=UTC)


def _outputs(available_power_w: float = 1_234.0, signal_quality: float = 0.25):
    thermal = SyntheticThermalOutput(
        timestamp_utc=T0, temp_sun_face_k=300.0, temp_shadow_face_k=200.0,
        temp_electronics_bay_k=295.0, q_solar_absorbed_w=0.0, q_radiated_w=0.0,
        q_internal_w=0.0, q_conductive_sun_elec_w=0.0, q_conductive_shadow_elec_w=0.0,
        q_heater_w=0.0, heater_active=False, heater_power_w=0.0, thermal_state="NOMINAL",
    )
    power = SyntheticPowerOutput(
        timestamp_utc=T0, solar_array_power_w=2_000.0, array_efficiency=0.28,
        total_load_w=1_200.0, battery_soc_pct=90.0, battery_voltage_v=28.0,
        battery_current_a=10.0, net_power_w=800.0, available_power_w=available_power_w,
        power_state="NOMINAL",
    )
    comms = SyntheticCommsOutput(
        timestamp_utc=T0, eirp_dbw=12.0, free_space_path_loss_db=200.0,
        received_power_dbw=-130.0, eb_n0_db=10.0, link_margin_db=8.0,
        data_rate_kbps=1939.4, signal_quality=signal_quality, comm_state="NOMINAL",
    )
    radiation = SyntheticRadiationOutput(
        timestamp_utc=T0, total_dose_rate_rad_s=0.001, cumulative_dose_krad=0.0,
        solar_array_degradation=1.0, thermal_alpha_degradation=1.0,
        thermal_eps_degradation=1.0, radiation_dose_rate_mrad_hr=0.1, sep_event_active=False,
    )
    return thermal, power, comms, radiation


def test_available_power_w_is_none_before_first_update():
    assert CrossModelBus().available_power_w is None


def test_update_passes_available_power_to_next_tick():
    bus = CrossModelBus()
    bus.update(*_outputs(available_power_w=1_234.0))
    assert bus.available_power_w == 1_234.0
    assert bus.to_cross_model_state(T0).available_power_w == 1_234.0


def test_update_does_not_feed_comms_signal_quality_back_as_plasma_noise():
    """plasma_noise_factor is a radiation output (contract 04), not comms' own output."""
    bus = CrossModelBus()
    bus.update(*_outputs(signal_quality=0.25))
    assert bus.plasma_noise_factor == 1.0


def test_reset_clears_available_power():
    bus = CrossModelBus()
    bus.update(*_outputs())
    bus.reset()
    assert bus.available_power_w is None
