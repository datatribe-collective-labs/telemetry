"""Fixtures for the packet module: one valid tick of model outputs."""

from datetime import UTC, datetime

import pytest
from contracts import (
    SyntheticCommsOutput,
    SyntheticMLFeatureVector,
    SyntheticPowerOutput,
    SyntheticRadiationOutput,
    SyntheticStateSnapshot,
    SyntheticThermalOutput,
)
from physics_models.packet import TickOutputs, assemble_packet

T0 = datetime(2026, 4, 6, 12, tzinfo=UTC)


@pytest.fixture
def make_outputs():
    """Build a valid TickOutputs; keyword dicts override fields of one model."""

    def _make(*, state=None, thermal=None, power=None, comms=None, radiation=None) -> TickOutputs:
        state_msg = SyntheticStateSnapshot(**{
            "timestamp_utc": T0, "x_km": 200_000.0, "y_km": 1.0, "z_km": 2.0, "vx_kms": 1.0,
            "vy_kms": 0.5, "vz_kms": 0.1, "distance_from_sun_au": 1.0, "solar_flux_w_m2": 1361.0,
            "solar_incidence_angle_deg": 10.0, "eclipse_state": "SUNLIT", "eclipse_fraction": 0.0,
            "earth_distance_km": 200_000.0, "dsn_visibility": True, "light_time_s": 0.67,
            "solar_array_angle_deg": 5.0, **(state or {}),
        })
        thermal_msg = SyntheticThermalOutput(**{
            "timestamp_utc": T0, "temp_sun_face_k": 350.0, "temp_shadow_face_k": 200.0,
            "temp_electronics_bay_k": 295.0, "q_solar_absorbed_w": 100.0, "q_radiated_w": 90.0,
            "q_internal_w": 10.0, "heater_active": False, "heater_power_w": 0.0,
            "thermal_state": "NOMINAL", **(thermal or {}),
        })
        power_msg = SyntheticPowerOutput(**{
            "timestamp_utc": T0, "solar_array_power_w": 11_000.0, "array_efficiency": 0.28,
            "total_load_w": 1_200.0, "battery_soc_pct": 90.0, "battery_voltage_v": 28.0,
            "battery_current_a": 10.0, "net_power_w": 9_800.0, "available_power_w": 9_320.0,
            "power_state": "NOMINAL", **(power or {}),
        })
        comms_msg = SyntheticCommsOutput(**{
            "timestamp_utc": T0, "eirp_dbw": 12.07, "free_space_path_loss_db": 205.0,
            "received_power_dbw": -137.0, "eb_n0_db": 11.0, "link_margin_db": 9.0,
            "data_rate_kbps": 1939.4, "signal_quality": 0.45, "comm_state": "NOMINAL",
            "link_loss_reason": "NONE", **(comms or {}),
        })
        radiation_msg = SyntheticRadiationOutput(**{
            "timestamp_utc": T0, "total_dose_rate_rad_s": 0.001, "cumulative_dose_krad": 0.0,
            "solar_array_degradation": 1.0, "thermal_alpha_degradation": 1.0,
            "thermal_eps_degradation": 1.0, "radiation_dose_rate_mrad_hr": 0.1,
            "sep_event_active": False, **(radiation or {}),
        })
        packet = assemble_packet(state_msg, thermal_msg, power_msg, comms_msg, radiation_msg)
        ml_features = SyntheticMLFeatureVector(
            timestamp_utc=T0, temp_elec_norm=0.5, temp_sun_norm=0.5, temp_shadow_norm=0.5,
            soc_norm=0.9, voltage_norm=0.9, signal_quality=packet.signal_quality, dose_rate_norm=0.0,
            r_re_norm=0.5, earth_dist_norm=0.5, eclipse_fraction=0.0, in_belt=0.0, sep_active=0.0,
            dsn_visible=1.0, temp_sun_residual_k=0.0, link_margin_residual_db=0.0,
            array_efficiency_ratio=1.0, voltage_residual_v=0.0, dose_rate_ratio=1.0,
            temp_elec_rate_k_min=0.0, soc_rate_pct_hr=0.0, dose_rate_delta_mrad_hr=0.0,
            signal_quality_delta=0.0,
        )
        return TickOutputs(state_msg, thermal_msg, power_msg, comms_msg, radiation_msg, packet, ml_features)

    return _make
