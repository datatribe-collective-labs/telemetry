"""Tests for assemble_packet."""

import pytest
from contracts import SyntheticTelemetryPacket

SOURCES = {
    "thermal": ("temp_sun_face_k", "temp_shadow_face_k", "temp_electronics_bay_k", "heater_active", "thermal_state"),
    "power": ("battery_voltage_v", "battery_soc_pct", "solar_array_power_w", "power_state"),
    "comms": ("signal_quality", "link_margin_db", "data_rate_kbps", "comm_state", "link_loss_reason"),
    "radiation": ("radiation_dose_rate_mrad_hr", "cumulative_dose_krad", "sep_event_active", "radiation_zone"),
    "state": ("timestamp_utc", "dsn_visibility"),
}


def test_assemble_packet_every_field_equals_its_source(make_outputs):
    outputs = make_outputs(radiation={"radiation_zone": "DEEP_SPACE"})
    for source, names in SOURCES.items():
        for name in names:
            assert getattr(outputs.packet, name) == getattr(getattr(outputs, source), name), name


def test_assemble_packet_sources_cover_every_packet_field():
    mapped = {name for names in SOURCES.values() for name in names}
    assert mapped | {"spacecraft_id", "all_nominal"} == set(SyntheticTelemetryPacket.model_fields)


def test_assemble_packet_identifies_orion(make_outputs):
    assert make_outputs().packet.spacecraft_id == "ORION_EM2"


def test_assemble_packet_all_nominal_when_every_subsystem_is_nominal(make_outputs):
    assert make_outputs().packet.all_nominal is True


@pytest.mark.parametrize(
    "override",
    [
        {"thermal": {"thermal_state": "HOT_LIMIT"}},
        {"power": {"power_state": "BATTERY_DISCHARGE"}},
        {"comms": {"comm_state": "DEGRADED"}},
    ],
)
def test_assemble_packet_not_all_nominal_when_a_subsystem_is_not(make_outputs, override):
    assert make_outputs(**override).packet.all_nominal is False


def test_assemble_packet_produced_on_no_link_ticks(make_outputs):
    packet = make_outputs(
        state={"dsn_visibility": False},
        comms={
            "comm_state": "NO_LINK", "link_loss_reason": "MOON_BLOCKED", "data_rate_kbps": 0.0,
            "signal_quality": 0.0, "link_margin_db": -190.0,
        },
    ).packet
    assert packet.comm_state == "NO_LINK"
    assert packet.link_loss_reason == "MOON_BLOCKED"
    assert packet.dsn_visibility is False
