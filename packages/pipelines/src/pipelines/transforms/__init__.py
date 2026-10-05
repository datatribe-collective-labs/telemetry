"""Physics transforms for space weather, radiation, and mission planning."""

from pipelines.transforms.planned_attitude import (
    ATTITUDE_MODE_DEFINITIONS,
    ATTITUDE_TIMELINE,
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
from pipelines.transforms.sgps_proton_flux import (
    CHANNEL_INDEX_TO_NAME,
    DIFFERENTIAL_PER_KEV,
    DIFFERENTIAL_PER_MEV,
    PFU,
    SgpsChannel,
    SgpsDerivationError,
    SgpsGe10Result,
    channels_from_table_rows,
    convert_differential_to_mev,
    derive_ge10_pfu,
)

__all__ = [
    # SGPS Proton Flux
    "SgpsChannel",
    "SgpsGe10Result",
    "SgpsDerivationError",
    "CHANNEL_INDEX_TO_NAME",
    "DIFFERENTIAL_PER_KEV",
    "DIFFERENTIAL_PER_MEV",
    "PFU",
    "convert_differential_to_mev",
    "derive_ge10_pfu",
    "channels_from_table_rows",
    # Planned Attitude
    "AttitudeMode",
    "AttitudeSegment",
    "ATTITUDE_TIMELINE",
    "ATTITUDE_MODE_DEFINITIONS",
    "parse_met",
    "format_met",
    "get_attitude_mode",
    "get_attitude_mode_at_met_str",
    "get_all_segments_for_mode",
    "get_total_duration_by_mode",
    "resolve_attitude",
    "get_mode_definition",
    "get_solar_incidence_angle_estimate",
    "get_solar_array_gimbal_estimate",
]