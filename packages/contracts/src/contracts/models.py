"""Pydantic models for the telemetry API contracts."""

from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field

# =============================================================================
# REAL DATA SOURCES (JPL/NASA) - Existing
# =============================================================================

class CloseApproach(BaseModel):
    """JPL Close-Approach Data (CAD) record."""

    model_config = ConfigDict(from_attributes=True)

    des: str = Field(..., description="Object designation")
    orbit_id: str = Field(..., description="Orbit solution ID")
    close_approach_jd: float = Field(..., description="Julian date of close approach")
    close_approach_time: datetime = Field(..., description="Close approach time (UTC)")
    dist_au: float | None = Field(None, description="Nominal distance in AU")
    dist_min_au: float | None = Field(None, description="Minimum distance in AU")
    dist_max_au: float | None = Field(None, description="Maximum distance in AU")
    v_rel_kms: float | None = Field(None, description="Relative velocity km/s")
    v_inf_kms: float | None = Field(None, description="Hyperbolic excess velocity km/s")
    h_mag: float | None = Field(None, description="Absolute magnitude")
    body: str = Field(default="Earth", description="Central body")


class OrionEphemeris(BaseModel):
    """JPL Horizons Orion spacecraft ephemeris record."""

    model_config = ConfigDict(from_attributes=True)

    target_id: str = Field(..., description="Target ID (default: -1024 for Orion)")
    epoch: datetime = Field(..., description="Ephemeris epoch (UTC)")
    jd: float = Field(..., description="Julian date")
    x_km: float | None = Field(None, description="X coordinate (km)")
    y_km: float | None = Field(None, description="Y coordinate (km)")
    z_km: float | None = Field(None, description="Z coordinate (km)")
    vx_kms: float | None = Field(None, description="X velocity (km/s)")
    vy_kms: float | None = Field(None, description="Y velocity (km/s)")
    vz_kms: float | None = Field(None, description="Z velocity (km/s)")
    speed_kms: float | None = Field(None, description="Speed magnitude (km/s)")
    light_time_s: float | None = Field(None, description="Light time (seconds)")
    range_km: float | None = Field(None, description="Range (km)")
    range_rate_kms: float | None = Field(None, description="Range rate (km/s)")


class DonkiEvent(BaseModel):
    """NASA DONKI space weather event record."""

    model_config = ConfigDict(from_attributes=True)

    event_type: str = Field(..., description="Event type (CME, SEP, FLR, etc.)")
    event_id: str = Field(..., description="Event-specific identifier")
    start_time: datetime | None = Field(None, description="Event start time (UTC)")
    end_time: datetime | None = Field(None, description="Event end time (UTC)")
    event_time: datetime | None = Field(None, description="Primary event time (UTC)")
    fetched_at: datetime = Field(..., description="When this record was fetched")
    source_url: str = Field(..., description="API URL used to fetch this event")
    payload: dict[str, Any] = Field(..., description="Complete DONKI JSON payload")


# =============================================================================
# NEW REAL DATA SOURCES
# =============================================================================

class GoesIntegralProtons(BaseModel):
    """GOES integral proton flux from NASA CCMC iSWA (HAPI)."""

    model_config = ConfigDict(from_attributes=True)

    time: datetime = Field(..., description="Observation time (UTC)")
    proton_satellite: str | None = Field(None, description="GOES satellite identifier")
    p1_pfu: float | None = Field(None, description="≥1 MeV integral flux (pfu)")
    p5_pfu: float | None = Field(None, description="≥5 MeV integral flux (pfu)")
    p10_pfu: float | None = Field(None, description="≥10 MeV integral flux (pfu)")
    p30_pfu: float | None = Field(None, description="≥30 MeV integral flux (pfu)")
    p50_pfu: float | None = Field(None, description="≥50 MeV integral flux (pfu)")
    p60_pfu: float | None = Field(None, description="≥60 MeV integral flux (pfu)")
    p100_pfu: float | None = Field(None, description="≥100 MeV integral flux (pfu)")
    p500_pfu: float | None = Field(None, description="≥500 MeV integral flux (pfu)")
    ingested_at: datetime = Field(..., description="When this record was ingested")


class DsnSiteGeometry(BaseModel):
    """JPL Horizons DSN site look angles for Orion spacecraft."""

    model_config = ConfigDict(from_attributes=True)

    target_id: str = Field(..., description="Target ID (default: -1024 for Orion)")
    site: str = Field(..., description="DSN antenna identifier (e.g., DSS-14)")
    complex: str = Field(..., description="DSN complex name (Goldstone, Canberra, Madrid)")
    epoch: datetime = Field(..., description="Ephemeris epoch (UTC)")
    azimuth_deg: float | None = Field(None, description="Azimuth angle (deg)")
    elevation_deg: float | None = Field(None, description="Elevation angle (deg)")
    range_km: float | None = Field(None, description="Range to spacecraft (km)")
    range_rate_kms: float | None = Field(None, description="Range rate (km/s)")
    light_time_s: float | None = Field(None, description="One-way light time (seconds)")
    visible: bool | None = Field(None, description="Visible above 10 deg elevation cutoff")
    ingested_at: datetime = Field(..., description="When this record was ingested")


# =============================================================================
# SYNTHETIC TELEMETRY (Physics Models) - New
# =============================================================================

class SyntheticStateSnapshot(BaseModel):
    """State engine snapshot - authoritative per-tick spacecraft state from OEM/Horizons.
    
    Replaces AROW attitude telemetry with physics model outputs.
    Source: 01_state_engine.odcs.yaml -> Kafka topic 'trajectory'
    """

    model_config = ConfigDict(from_attributes=True)

    timestamp_utc: datetime = Field(..., description="Tick timestamp (UTC)")
    x_km: float = Field(..., description="Position X (geocentric EME2000, km)")
    y_km: float = Field(..., description="Position Y (geocentric EME2000, km)")
    z_km: float = Field(..., description="Position Z (geocentric EME2000, km)")
    vx_kms: float = Field(..., description="Velocity X (km/s)")
    vy_kms: float = Field(..., description="Velocity Y (km/s)")
    vz_kms: float = Field(..., description="Velocity Z (km/s)")
    distance_from_sun_au: float = Field(..., description="Heliocentric distance (AU)")
    solar_flux_w_m2: float = Field(..., description="Solar irradiance at spacecraft (W/m²)")
    solar_incidence_angle_deg: float = Field(..., description="Solar incidence angle (deg)")
    eclipse_state: Literal["SUNLIT", "UMBRA", "PENUMBRA"] = Field(..., description="Shadow condition")
    eclipse_fraction: float = Field(..., description="Eclipse fraction (0-1)")
    earth_distance_km: float = Field(..., description="Earth-to-spacecraft distance (km)")
    dsn_visibility: bool = Field(..., description="DSN line-of-sight available")
    light_time_s: float = Field(..., description="One-way light time (s)")
    solar_array_angle_deg: float = Field(..., description="Solar array gimbal offset (deg)")
    roll_deg: float | None = Field(None, description="Spacecraft roll (deg)")
    pitch_deg: float | None = Field(None, description="Spacecraft pitch (deg)")
    yaw_deg: float | None = Field(None, description="Spacecraft yaw (deg)")


class SyntheticThermalOutput(BaseModel):
    """Thermal model output - three-node lumped parameter model.
    
    Source: 02_thermal_model.odcs.yaml -> Kafka topic 'telemetry'
    """

    model_config = ConfigDict(from_attributes=True)

    timestamp_utc: datetime = Field(..., description="Tick timestamp (UTC)")
    temp_sun_face_k: float = Field(..., description="Sun-facing surface temperature (K)")
    temp_shadow_face_k: float = Field(..., description="Shadow-facing surface temperature (K)")
    temp_electronics_bay_k: float = Field(..., description="Electronics bay temperature (K)")
    q_solar_absorbed_w: float = Field(..., description="Solar flux absorbed by sun-face (W)")
    q_radiated_w: float = Field(..., description="Total radiative heat rejection (W)")
    q_internal_w: float = Field(..., description="Internal power dissipation (W)")
    heater_active: bool = Field(..., description="Survival heater active")
    heater_power_w: float = Field(..., description="Heater power draw (W)")
    thermal_state: Literal["NOMINAL", "COLD_SURVIVAL", "HOT_LIMIT"] = Field(..., description="Thermal health state")


class SyntheticPowerOutput(BaseModel):
    """Power model output - electrical power system model.
    
    Source: 03_power_comms_radiation.odcs.yaml -> Kafka topic 'telemetry'
    """

    model_config = ConfigDict(from_attributes=True)

    timestamp_utc: datetime = Field(..., description="Tick timestamp (UTC)")
    solar_array_power_w: float = Field(..., description="Solar array gross output (W)")
    array_efficiency: float = Field(..., description="Effective solar array efficiency (0-1)")
    total_load_w: float = Field(..., description="Total spacecraft electrical load (W)")
    battery_soc_pct: float = Field(..., description="Battery state of charge (%)")
    battery_voltage_v: float = Field(..., description="Battery bus voltage (V)")
    battery_current_a: float = Field(..., description="Battery current (A, +charge/-discharge)")
    net_power_w: float = Field(..., description="Net spacecraft electrical power before battery flow (W)")
    available_power_w: float = Field(..., description="Available power headroom for non-essential loads (W)")
    power_state: Literal["NOMINAL", "BATTERY_DISCHARGE", "LOW_POWER_MODE", "CRITICAL"] = Field(..., description="Power health state")


class SyntheticCommsOutput(BaseModel):
    """Communications model output - S-band link budget.
    
    Source: 03_power_comms_radiation.odcs.yaml -> Kafka topic 'telemetry'
    """

    model_config = ConfigDict(from_attributes=True)

    timestamp_utc: datetime = Field(..., description="Tick timestamp (UTC)")
    eirp_dbw: float = Field(..., description="EIRP (dBW)")
    free_space_path_loss_db: float = Field(..., description="Free-space path loss (dB)")
    received_power_dbw: float = Field(..., description="Received power at DSN (dBW)")
    eb_n0_db: float = Field(..., description="Eb/N0 - bit energy to noise density ratio (dB)")
    link_margin_db: float = Field(..., description="Link margin above required Eb/N0 (dB)")
    data_rate_kbps: float = Field(..., description="Downlink data rate (kbps)")
    signal_quality: float = Field(..., description="Signal quality index (0-1)")
    comm_state: Literal["NOMINAL", "DEGRADED", "NO_LINK"] = Field(..., description="Communications link state")


class SyntheticRadiationOutput(BaseModel):
    """Radiation model output - dose accumulation and degradation.
    
    Source: 03_power_comms_radiation.odcs.yaml -> Kafka topic 'telemetry'
    """

    model_config = ConfigDict(from_attributes=True)

    timestamp_utc: datetime = Field(..., description="Tick timestamp (UTC)")
    total_dose_rate_rad_s: float = Field(..., description="Total absorbed dose rate (rad/s)")
    cumulative_dose_krad: float = Field(..., description="Cumulative absorbed dose (krad Si)")
    solar_array_degradation: float = Field(..., description="Solar array degradation factor (relative to BOL)")
    thermal_alpha_degradation: float = Field(..., description="Thermal coating absorptivity factor")
    thermal_eps_degradation: float = Field(..., description="Thermal coating emissivity factor")
    radiation_dose_rate_mrad_hr: float = Field(..., description="Dose rate in mrad/hr")
    sep_event_active: bool = Field(..., description="SEP event in progress")


class SyntheticCrossModelState(BaseModel):
    """Cross-model coupling bus - internal pipeline topic.
    
    Source: 04_cross_model_telemetry_packet.odcs.yaml -> Kafka topic 'cross_model_state'
    """

    model_config = ConfigDict(from_attributes=True)

    timestamp_utc: datetime = Field(..., description="Tick timestamp (UTC)")
    electronics_bay_temp_k: float = Field(..., description="Electronics bay temp from thermal model (K)")
    power_dissipation_w: float = Field(..., description="Waste heat from electronics (W)")
    available_power_w: float = Field(..., description="Available power for non-essential loads (W)")
    solar_array_degradation_factor: float = Field(..., description="Solar array degradation from radiation model")
    thermal_coating_alpha_factor: float = Field(..., description="Absorptivity degradation factor")
    thermal_coating_eps_factor: float = Field(..., description="Emissivity degradation factor")
    plasma_noise_factor: float = Field(..., description="Ionospheric plasma noise factor (quality degradation multiplier)")


class SyntheticTelemetryPacket(BaseModel):
    """Synthesized telemetry packet - primary output combining all physics models.
    
    This is the main consumer-facing contract (dashboard, replay, Superset).
    Source: 04_cross_model_telemetry_packet.odcs.yaml -> Kafka topic 'telemetry' + TimescaleDB
    """

    model_config = ConfigDict(from_attributes=True)

    timestamp_utc: datetime = Field(..., description="Tick timestamp (UTC)")
    spacecraft_id: str = Field(default="ORION_EM2", description="Spacecraft identifier")

    # Thermal fields
    temp_sun_face_k: float = Field(..., description="Sun-facing surface temperature (K)")
    temp_shadow_face_k: float = Field(..., description="Shadow-facing surface temperature (K)")
    temp_electronics_bay_k: float = Field(..., description="Electronics bay temperature (K)")
    heater_active: bool = Field(..., description="Survival heater active")
    thermal_state: Literal["NOMINAL", "COLD_SURVIVAL", "HOT_LIMIT"] = Field(..., description="Thermal health state")

    # Power fields
    battery_voltage_v: float = Field(..., description="Battery voltage (V)")
    battery_soc_pct: float = Field(..., description="Battery state of charge (%)")
    solar_array_power_w: float = Field(..., description="Solar array power (W)")
    power_state: Literal["NOMINAL", "BATTERY_DISCHARGE", "LOW_POWER_MODE", "CRITICAL"] = Field(..., description="Power health state")

    # Comms fields
    signal_quality: float = Field(..., description="Signal quality index (0-1)")
    link_margin_db: float = Field(..., description="Link margin (dB)")
    data_rate_kbps: float = Field(..., description="Downlink data rate (kbps)")
    comm_state: Literal["NOMINAL", "DEGRADED", "NO_LINK"] = Field(..., description="Communications link state")

    # Radiation fields
    radiation_dose_rate_mrad_hr: float = Field(..., description="Dose rate (mrad/hr)")
    cumulative_dose_krad: float = Field(..., description="Cumulative dose (krad Si)")
    sep_event_active: bool = Field(..., description="SEP event active")

    # Derived health rollup
    all_nominal: bool = Field(..., description="All subsystems nominal (thermal=power=comms=NOMINAL)")


class SyntheticAnomalyEvent(BaseModel):
    """Anomaly event from two-layer detection system.
    
    Source: 05_anomaly_ml_features.odcs.yaml -> Kafka topic 'events'
    """

    model_config = ConfigDict(from_attributes=True)

    event_id: str = Field(..., description="Unique event identifier (UUID)")
    timestamp_utc: datetime = Field(..., description="Event detection timestamp (UTC)")
    anomaly_type: str = Field(..., description="Anomaly type code")
    detection_layer: Literal[1, 2, 3] = Field(..., description="Detection layer (1=contract, 2=rules, 3=ML)")
    severity: Literal["CRITICAL", "ALERT", "WARNING", "INFO"] = Field(..., description="Anomaly severity")
    description: str = Field(..., description="Human-readable anomaly description")
    field_name: str = Field(..., description="Primary field that triggered the anomaly")
    field_value: float = Field(..., description="Value of the triggering field")
    expected_value: float | None = Field(None, description="Physics-baseline expected value")
    residual: float | None = Field(None, description="Actual minus expected (anomaly signal)")
    contract_reference: str = Field(..., description="ODCS contract file and quality rule")
    suggested_cause: str = Field(..., description="Most likely physical explanation")
    r_re: float = Field(..., description="Spacecraft position in Earth radii")
    mission_phase: str = Field(..., description="Mission phase at event time")
    ml_anomaly_score: float | None = Field(None, description="ML model anomaly score (0-1)")


class SyntheticMLFeatureVector(BaseModel):
    """ML feature vector for anomaly detection training/inference.
    
    Source: 05_anomaly_ml_features.odcs.yaml -> Kafka topic 'ml_features'
    """

    model_config = ConfigDict(from_attributes=True)

    timestamp_utc: datetime = Field(..., description="Tick timestamp (UTC)")

    # Raw normalized features
    temp_elec_norm: float = Field(..., description="Electronics bay temperature, normalized [0,1]")
    temp_sun_norm: float = Field(..., description="Sun-face temperature, normalized [0,1]")
    temp_shadow_norm: float = Field(..., description="Shadow-face temperature, normalized [0,1]")
    soc_norm: float = Field(..., description="Battery SoC, normalized [0,1]")
    voltage_norm: float = Field(..., description="Battery voltage, normalized [0,1]")
    signal_quality: float = Field(..., description="Signal quality (already normalized [0,1])")
    dose_rate_norm: float = Field(..., description="Radiation dose rate, normalized [0,1]")

    # Context features
    r_re_norm: float = Field(..., description="Earth radii distance, normalized [0,1]")
    earth_dist_norm: float = Field(..., description="Earth distance, normalized [0,1]")
    eclipse_fraction: float = Field(..., description="Eclipse fraction [0,1]")
    in_belt: float = Field(..., description="In Van Allen belt (binary)")
    sep_active: float = Field(..., description="SEP event active (binary)")
    dsn_visible: float = Field(..., description="DSN line-of-sight available (binary)")

    # Physics residual features
    temp_sun_residual_k: float = Field(..., description="Sun-face temp residual vs equilibrium (K)")
    link_margin_residual_db: float = Field(..., description="Link margin residual vs Friis (dB)")
    array_efficiency_ratio: float = Field(..., description="Actual vs expected array output ratio")
    voltage_residual_v: float = Field(..., description="Battery voltage residual vs SoC model (V)")
    dose_rate_ratio: float = Field(..., description="Actual vs expected belt-model dose rate ratio")

    # Rate-of-change features
    temp_elec_rate_k_min: float = Field(..., description="Electronics temp rate of change (K/min)")
    soc_rate_pct_hr: float = Field(..., description="Battery SoC rate of change (%/hr)")
    dose_rate_delta_mrad_hr: float = Field(..., description="Dose rate change between ticks (mrad/hr)")
    signal_quality_delta: float = Field(..., description="Signal quality change between ticks")


# =============================================================================
# Request/Response Models for API Endpoints
# =============================================================================

# --- Real Data Sources ---

class CloseApproachQueryParams(BaseModel):
    """Query parameters for close approaches endpoint."""
    date_from: datetime | None = Field(None, description="Start date (UTC)")
    date_to: datetime | None = Field(None, description="End date (UTC)")
    dist_max_au: float = Field(default=0.05, description="Maximum distance in AU")
    designation: str | None = Field(None, description="Filter by object designation (partial match)")
    limit: int = Field(default=100, ge=1, le=1000, description="Maximum results")
    offset: int = Field(default=0, ge=0, description="Pagination offset")


class CloseApproachResponse(BaseModel):
    """Response for close approaches endpoint."""
    items: list[CloseApproach]
    total: int
    limit: int
    offset: int


class OrionEphemerisQueryParams(BaseModel):
    """Query parameters for Orion ephemeris endpoint."""
    date_from: datetime | None = Field(None, description="Start date (UTC)")
    date_to: datetime | None = Field(None, description="End date (UTC)")
    target_id: str = Field(default="-1024", description="Target ID")
    limit: int = Field(default=100, ge=1, le=1000, description="Maximum results")
    offset: int = Field(default=0, ge=0, description="Pagination offset")


class OrionEphemerisResponse(BaseModel):
    """Response for Orion ephemeris endpoint."""
    items: list[OrionEphemeris]
    total: int
    limit: int
    offset: int


class DonkiEventQueryParams(BaseModel):
    """Query parameters for DONKI events endpoint."""
    date_from: datetime | None = Field(None, description="Start date (UTC)")
    date_to: datetime | None = Field(None, description="End date (UTC)")
    event_types: list[str] | None = Field(None, description="Filter by event types")
    limit: int = Field(default=100, ge=1, le=1000, description="Maximum results")
    offset: int = Field(default=0, ge=0, description="Pagination offset")


class DonkiEventResponse(BaseModel):
    """Response for DONKI events endpoint."""
    items: list[DonkiEvent]
    total: int
    limit: int
    offset: int


class GoesIntegralProtonsQueryParams(BaseModel):
    """Query parameters for GOES integral protons endpoint."""
    date_from: datetime | None = Field(None, description="Start date (UTC)")
    date_to: datetime | None = Field(None, description="End date (UTC)")
    limit: int = Field(default=100, ge=1, le=1000, description="Maximum results")
    offset: int = Field(default=0, ge=0, description="Pagination offset")


class GoesIntegralProtonsResponse(BaseModel):
    """Response for GOES integral protons endpoint."""
    items: list[GoesIntegralProtons]
    total: int
    limit: int
    offset: int


class DsnSiteGeometryQueryParams(BaseModel):
    """Query parameters for DSN site geometry endpoint."""
    date_from: datetime | None = Field(None, description="Start date (UTC)")
    date_to: datetime | None = Field(None, description="End date (UTC)")
    site: str | None = Field(None, description="Filter by DSN site (e.g., DSS-14)")
    complex: str | None = Field(None, description="Filter by DSN complex (Goldstone, Canberra, Madrid)")
    visible_only: bool = Field(default=False, description="Only return visible passes (elevation >= 10 deg)")
    limit: int = Field(default=100, ge=1, le=1000, description="Maximum results")
    offset: int = Field(default=0, ge=0, description="Pagination offset")


class DsnSiteGeometryResponse(BaseModel):
    """Response for DSN site geometry endpoint."""
    items: list[DsnSiteGeometry]
    total: int
    limit: int
    offset: int


# --- Synthetic Telemetry ---

class SyntheticTelemetryQueryParams(BaseModel):
    """Common query parameters for synthetic telemetry endpoints."""
    date_from: datetime | None = Field(None, description="Start date (UTC)")
    date_to: datetime | None = Field(None, description="End date (UTC)")
    limit: int = Field(default=100, ge=1, le=1000, description="Maximum results")
    offset: int = Field(default=0, ge=0, description="Pagination offset")


class SyntheticStateResponse(BaseModel):
    items: list[SyntheticStateSnapshot]
    total: int
    limit: int
    offset: int


class SyntheticThermalResponse(BaseModel):
    items: list[SyntheticThermalOutput]
    total: int
    limit: int
    offset: int


class SyntheticPowerResponse(BaseModel):
    items: list[SyntheticPowerOutput]
    total: int
    limit: int
    offset: int


class SyntheticCommsResponse(BaseModel):
    items: list[SyntheticCommsOutput]
    total: int
    limit: int
    offset: int


class SyntheticRadiationResponse(BaseModel):
    items: list[SyntheticRadiationOutput]
    total: int
    limit: int
    offset: int


class SyntheticCrossModelResponse(BaseModel):
    items: list[SyntheticCrossModelState]
    total: int
    limit: int
    offset: int


class SyntheticTelemetryPacketResponse(BaseModel):
    items: list[SyntheticTelemetryPacket]
    total: int
    limit: int
    offset: int


class SyntheticAnomalyResponse(BaseModel):
    items: list[SyntheticAnomalyEvent]
    total: int
    limit: int
    offset: int


class SyntheticMLFeaturesResponse(BaseModel):
    items: list[SyntheticMLFeatureVector]
    total: int
    limit: int
    offset: int


# --- Health ---

class HealthResponse(BaseModel):
    """Health check response."""
    status: str = "ok"
    service: str = "telemetry-api"
    version: str = "0.1.0"

# --- NASA OEM ephemeris (mission planning arcs) ---

class OemStateVector(BaseModel):
    """One state vector from a NASA CCSDS OEM arc (EME2000, Earth-centered)."""
    arc_id: str = Field(..., description="Planning arc identifier (source zip member stem)")
    epoch: datetime
    x_km: float | None = None
    y_km: float | None = None
    z_km: float | None = None
    vx_kms: float | None = None
    vy_kms: float | None = None
    vz_kms: float | None = None
    range_km: float | None = None
    speed_kms: float | None = None


class OemStateVectorResponse(BaseModel):
    """Response for OEM state vectors endpoint."""
    items: list[OemStateVector]
    total: int
    limit: int
    offset: int


# --- Mission timeline events (DRAFT — extracted PDF timeline, unvalidated) ---

class MissionEvent(BaseModel):
    """One planned mission segment keyed by Mission Elapsed Time.

    DRAFT: extracted from the graphical Artemis II Overview Timeline PDF but not
    yet fact-checked against it.
    """
    met_start_s: float = Field(..., description="MET start (seconds from liftoff)")
    met_end_s: float = Field(..., description="MET end, exclusive (seconds from liftoff)")
    mode: str = Field(..., description="Attitude mode (e.g. BURN_TLI, EDL)")
    description: str


class MissionEventResponse(BaseModel):
    """Response for mission events endpoint."""
    items: list[MissionEvent]
    total: int
