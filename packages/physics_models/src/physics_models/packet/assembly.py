"""Build the telemetry packet: Orion's onboard state at one tick (ODCS 04)."""

from contracts import (
    SyntheticCommsOutput,
    SyntheticPowerOutput,
    SyntheticRadiationOutput,
    SyntheticStateSnapshot,
    SyntheticTelemetryPacket,
    SyntheticThermalOutput,
)


def assemble_packet(
    state: SyntheticStateSnapshot,
    thermal: SyntheticThermalOutput,
    power: SyntheticPowerOutput,
    comms: SyntheticCommsOutput,
    radiation: SyntheticRadiationOutput,
) -> SyntheticTelemetryPacket:
    """Combine one tick's model outputs. Produced on NO_LINK ticks too."""
    return SyntheticTelemetryPacket(
        timestamp_utc=state.timestamp_utc,
        spacecraft_id="ORION_EM2",
        # Thermal
        temp_sun_face_k=thermal.temp_sun_face_k,
        temp_shadow_face_k=thermal.temp_shadow_face_k,
        temp_electronics_bay_k=thermal.temp_electronics_bay_k,
        heater_active=thermal.heater_active,
        thermal_state=thermal.thermal_state,
        # Power
        battery_voltage_v=power.battery_voltage_v,
        battery_soc_pct=power.battery_soc_pct,
        solar_array_power_w=power.solar_array_power_w,
        power_state=power.power_state,
        # Comms
        signal_quality=comms.signal_quality,
        link_margin_db=comms.link_margin_db,
        data_rate_kbps=comms.data_rate_kbps,
        comm_state=comms.comm_state,
        link_loss_reason=comms.link_loss_reason,
        dsn_visibility=state.dsn_visibility,
        # Radiation
        radiation_dose_rate_mrad_hr=radiation.radiation_dose_rate_mrad_hr,
        cumulative_dose_krad=radiation.cumulative_dose_krad,
        sep_event_active=radiation.sep_event_active,
        radiation_zone=radiation.radiation_zone,
        # Derived
        all_nominal=(
            thermal.thermal_state == "NOMINAL"
            and power.power_state == "NOMINAL"
            and comms.comm_state == "NOMINAL"
        ),
    )
