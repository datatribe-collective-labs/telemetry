"""State engine generator - authoritative spacecraft state."""

from contracts.planned_attitude import (
    AttitudeMode,
    AttitudeSegment,
    format_met,
    get_all_segments_for_mode,
    get_attitude_mode,
    get_attitude_mode_at_met_str,
    get_mode_definition,
    get_solar_array_gimbal_estimate,
    get_solar_incidence_angle_estimate,
    get_total_duration_by_mode,
    parse_met,
    resolve_attitude,
)

__all__ = [
    "AttitudeMode",
    "AttitudeSegment",
    "format_met",
    "get_all_segments_for_mode",
    "get_attitude_mode",
    "get_attitude_mode_at_met_str",
    "get_mode_definition",
    "get_solar_array_gimbal_estimate",
    "get_solar_incidence_angle_estimate",
    "get_total_duration_by_mode",
    "parse_met",
    "resolve_attitude",
]