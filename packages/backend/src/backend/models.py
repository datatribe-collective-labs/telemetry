"""SQLAlchemy ORM models for all application tables.

Synthetic telemetry tables (lowercase snake_case columns, TimescaleDB hypertables)
and real-data tables (mixed-case column names, managed by JPL/NASA).

All models inherit from the same Base; Alembic autogenerate uses target_metadata
derived from this Base to compare against the live database schema.
"""

import uuid
from datetime import datetime

from sqlalchemy import (
    Boolean,
    DateTime,
    Double,
    Index,
    SmallInteger,
    String,
    Text,
    Uuid,
    desc,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    """Base class for all application database models."""


class StateSnapshot(Base):
    """State engine snapshot - authoritative per-tick spacecraft state."""

    __tablename__ = "state_snapshot"

    timestamp_utc: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), primary_key=True
    )
    x_km: Mapped[float] = mapped_column(Double, nullable=False)
    y_km: Mapped[float] = mapped_column(Double, nullable=False)
    z_km: Mapped[float] = mapped_column(Double, nullable=False)
    vx_kms: Mapped[float] = mapped_column(Double, nullable=False)
    vy_kms: Mapped[float] = mapped_column(Double, nullable=False)
    vz_kms: Mapped[float] = mapped_column(Double, nullable=False)
    distance_from_sun_au: Mapped[float] = mapped_column(Double, nullable=False)
    solar_flux_w_m2: Mapped[float] = mapped_column(Double, nullable=False)
    solar_incidence_angle_deg: Mapped[float] = mapped_column(Double, nullable=False)
    eclipse_state: Mapped[str] = mapped_column(String(10), nullable=False)
    eclipse_fraction: Mapped[float] = mapped_column(Double, nullable=False)
    earth_distance_km: Mapped[float] = mapped_column(Double, nullable=False)
    dsn_visibility: Mapped[bool] = mapped_column(Boolean, nullable=False)
    light_time_s: Mapped[float] = mapped_column(Double, nullable=False)
    solar_array_angle_deg: Mapped[float] = mapped_column(Double, nullable=False)
    roll_deg: Mapped[float | None] = mapped_column(Double, nullable=True)
    pitch_deg: Mapped[float | None] = mapped_column(Double, nullable=True)
    yaw_deg: Mapped[float | None] = mapped_column(Double, nullable=True)

    __table_args__ = (
        Index("idx_state_snapshot_eclipse", "eclipse_state", "timestamp_utc"),
    )


class ThermalOutput(Base):
    """Thermal model output - three-node lumped parameter model."""

    __tablename__ = "thermal_output"

    timestamp_utc: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), primary_key=True
    )
    temp_sun_face_k: Mapped[float] = mapped_column(Double, nullable=False)
    temp_shadow_face_k: Mapped[float] = mapped_column(Double, nullable=False)
    temp_electronics_bay_k: Mapped[float] = mapped_column(Double, nullable=False)
    q_solar_absorbed_w: Mapped[float] = mapped_column(Double, nullable=False)
    q_radiated_w: Mapped[float] = mapped_column(Double, nullable=False)
    q_internal_w: Mapped[float] = mapped_column(Double, nullable=False)
    heater_active: Mapped[bool] = mapped_column(Boolean, nullable=False)
    heater_power_w: Mapped[float] = mapped_column(Double, nullable=False)
    thermal_state: Mapped[str] = mapped_column(String(20), nullable=False)

    __table_args__ = (
        Index("idx_thermal_output_state", "thermal_state", "timestamp_utc"),
    )


class PowerOutput(Base):
    """Power model output - electrical power system."""

    __tablename__ = "power_output"

    timestamp_utc: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), primary_key=True
    )
    solar_array_power_w: Mapped[float] = mapped_column(Double, nullable=False)
    array_efficiency: Mapped[float] = mapped_column(Double, nullable=False)
    total_load_w: Mapped[float] = mapped_column(Double, nullable=False)
    battery_soc_pct: Mapped[float] = mapped_column(Double, nullable=False)
    battery_voltage_v: Mapped[float] = mapped_column(Double, nullable=False)
    battery_current_a: Mapped[float] = mapped_column(Double, nullable=False)
    net_power_w: Mapped[float] = mapped_column(Double, nullable=False)
    available_power_w: Mapped[float] = mapped_column(Double, nullable=False)
    power_state: Mapped[str] = mapped_column(String(20), nullable=False)

    __table_args__ = (
        Index("idx_power_output_state", "power_state", "timestamp_utc"),
        Index("idx_power_output_soc", "battery_soc_pct", "timestamp_utc"),
    )


class CommsOutput(Base):
    """Comms model output - S-band link budget."""

    __tablename__ = "comms_output"

    timestamp_utc: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), primary_key=True
    )
    eirp_dbw: Mapped[float] = mapped_column(Double, nullable=False)
    free_space_path_loss_db: Mapped[float] = mapped_column(Double, nullable=False)
    received_power_dbw: Mapped[float] = mapped_column(Double, nullable=False)
    eb_n0_db: Mapped[float] = mapped_column(Double, nullable=False)
    link_margin_db: Mapped[float] = mapped_column(Double, nullable=False)
    data_rate_kbps: Mapped[float] = mapped_column(Double, nullable=False)
    signal_quality: Mapped[float] = mapped_column(Double, nullable=False)
    comm_state: Mapped[str] = mapped_column(String(10), nullable=False)

    __table_args__ = (
        Index("idx_comms_output_state", "comm_state", "timestamp_utc"),
    )


class RadiationOutput(Base):
    """Radiation model output - dose accumulation and degradation."""

    __tablename__ = "radiation_output"

    timestamp_utc: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), primary_key=True
    )
    total_dose_rate_rad_s: Mapped[float] = mapped_column(Double, nullable=False)
    cumulative_dose_krad: Mapped[float] = mapped_column(Double, nullable=False)
    solar_array_degradation: Mapped[float] = mapped_column(Double, nullable=False)
    thermal_alpha_degradation: Mapped[float] = mapped_column(Double, nullable=False)
    thermal_eps_degradation: Mapped[float] = mapped_column(Double, nullable=False)
    radiation_dose_rate_mrad_hr: Mapped[float] = mapped_column(Double, nullable=False)
    sep_event_active: Mapped[bool] = mapped_column(Boolean, nullable=False)

    __table_args__ = (
        Index("idx_radiation_output_sep", "sep_event_active", "timestamp_utc"),
        Index("idx_radiation_output_cumulative", "cumulative_dose_krad", "timestamp_utc"),
    )


class CrossModelState(Base):
    """Cross-model coupling state - internal pipeline bus."""

    __tablename__ = "cross_model_state"

    timestamp_utc: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), primary_key=True
    )
    electronics_bay_temp_k: Mapped[float] = mapped_column(Double, nullable=False)
    power_dissipation_w: Mapped[float] = mapped_column(Double, nullable=False)
    available_power_w: Mapped[float] = mapped_column(Double, nullable=False)
    solar_array_degradation_factor: Mapped[float] = mapped_column(Double, nullable=False)
    thermal_coating_alpha_factor: Mapped[float] = mapped_column(Double, nullable=False)
    thermal_coating_eps_factor: Mapped[float] = mapped_column(Double, nullable=False)
    plasma_noise_factor: Mapped[float] = mapped_column(Double, nullable=False)


class TelemetryPacket(Base):
    """Synthesized telemetry packet - primary consumer-facing output."""

    __tablename__ = "telemetry_packet"

    timestamp_utc: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), primary_key=True
    )
    spacecraft_id: Mapped[str] = mapped_column(
        String(10), nullable=False, default="ORION_EM2"
    )
    # Thermal fields
    temp_sun_face_k: Mapped[float] = mapped_column(Double, nullable=False)
    temp_shadow_face_k: Mapped[float] = mapped_column(Double, nullable=False)
    temp_electronics_bay_k: Mapped[float] = mapped_column(Double, nullable=False)
    heater_active: Mapped[bool] = mapped_column(Boolean, nullable=False)
    thermal_state: Mapped[str] = mapped_column(String(20), nullable=False)
    # Power fields
    battery_voltage_v: Mapped[float] = mapped_column(Double, nullable=False)
    battery_soc_pct: Mapped[float] = mapped_column(Double, nullable=False)
    solar_array_power_w: Mapped[float] = mapped_column(Double, nullable=False)
    power_state: Mapped[str] = mapped_column(String(20), nullable=False)
    # Comms fields
    signal_quality: Mapped[float] = mapped_column(Double, nullable=False)
    link_margin_db: Mapped[float] = mapped_column(Double, nullable=False)
    data_rate_kbps: Mapped[float] = mapped_column(Double, nullable=False)
    comm_state: Mapped[str] = mapped_column(String(10), nullable=False)
    # Radiation fields
    radiation_dose_rate_mrad_hr: Mapped[float] = mapped_column(Double, nullable=False)
    cumulative_dose_krad: Mapped[float] = mapped_column(Double, nullable=False)
    sep_event_active: Mapped[bool] = mapped_column(Boolean, nullable=False)
    # Derived health rollup
    all_nominal: Mapped[bool] = mapped_column(Boolean, nullable=False)

    __table_args__ = (
        Index("idx_telemetry_packet_all_nominal", "all_nominal", "timestamp_utc"),
        Index(
            "idx_telemetry_packet_states",
            "thermal_state",
            "power_state",
            "comm_state",
            "timestamp_utc",
        ),
        Index("idx_telemetry_packet_soc", "battery_soc_pct", "timestamp_utc"),
    )


class AnomalyEvent(Base):
    """Anomaly event from two-layer detection system."""

    __tablename__ = "anomaly_events"

    event_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, primary_key=True, default=uuid.uuid4
    )
    timestamp_utc: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), primary_key=True
    )
    anomaly_type: Mapped[str] = mapped_column(String(40), nullable=False)
    detection_layer: Mapped[int] = mapped_column(SmallInteger, nullable=False)
    severity: Mapped[str] = mapped_column(String(10), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    field_name: Mapped[str] = mapped_column(String(60), nullable=False)
    field_value: Mapped[float] = mapped_column(Double, nullable=False)
    expected_value: Mapped[float | None] = mapped_column(Double, nullable=True)
    residual: Mapped[float | None] = mapped_column(Double, nullable=True)
    contract_reference: Mapped[str] = mapped_column(String(120), nullable=False)
    suggested_cause: Mapped[str] = mapped_column(Text, nullable=False)
    r_re: Mapped[float] = mapped_column(Double, nullable=False)
    mission_phase: Mapped[str] = mapped_column(String(20), nullable=False)
    ml_anomaly_score: Mapped[float | None] = mapped_column(Double, nullable=True)

    __table_args__ = (
        Index("idx_anomaly_events_type", "anomaly_type", "timestamp_utc"),
        Index("idx_anomaly_events_layer", "detection_layer", "timestamp_utc"),
        Index("idx_anomaly_events_severity", "severity", "timestamp_utc"),
        Index("idx_anomaly_events_phase", "mission_phase", "timestamp_utc"),
    )


class MLFeatureVector(Base):
    """ML feature vector for anomaly detection."""

    __tablename__ = "ml_feature_vectors"

    timestamp_utc: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), primary_key=True
    )
    # Raw normalized features
    temp_elec_norm: Mapped[float] = mapped_column(Double, nullable=False)
    temp_sun_norm: Mapped[float] = mapped_column(Double, nullable=False)
    temp_shadow_norm: Mapped[float] = mapped_column(Double, nullable=False)
    soc_norm: Mapped[float] = mapped_column(Double, nullable=False)
    voltage_norm: Mapped[float] = mapped_column(Double, nullable=False)
    signal_quality: Mapped[float] = mapped_column(Double, nullable=False)
    dose_rate_norm: Mapped[float] = mapped_column(Double, nullable=False)
    # Context features
    r_re_norm: Mapped[float] = mapped_column(Double, nullable=False)
    earth_dist_norm: Mapped[float] = mapped_column(Double, nullable=False)
    eclipse_fraction: Mapped[float] = mapped_column(Double, nullable=False)
    in_belt: Mapped[float] = mapped_column(Double, nullable=False)
    sep_active: Mapped[float] = mapped_column(Double, nullable=False)
    dsn_visible: Mapped[float] = mapped_column(Double, nullable=False)
    # Physics residual features
    temp_sun_residual_k: Mapped[float] = mapped_column(Double, nullable=False)
    link_margin_residual_db: Mapped[float] = mapped_column(Double, nullable=False)
    array_efficiency_ratio: Mapped[float] = mapped_column(Double, nullable=False)
    voltage_residual_v: Mapped[float] = mapped_column(Double, nullable=False)
    dose_rate_ratio: Mapped[float] = mapped_column(Double, nullable=False)
    # Rate-of-change features
    temp_elec_rate_k_min: Mapped[float] = mapped_column(Double, nullable=False)
    soc_rate_pct_hr: Mapped[float] = mapped_column(Double, nullable=False)
    dose_rate_delta_mrad_hr: Mapped[float] = mapped_column(Double, nullable=False)
    signal_quality_delta: Mapped[float] = mapped_column(Double, nullable=False)


# ---- Real-data tables (JPL/NASA managed, NOT TimescaleDB hypertables) ----

class CloseApproach(Base):
    """JPL Close-Approach Data (CAD) record.

    Managed externally; Alembic now tracks schema but does not inject
    TimescaleDB hypertable operations.
    """

    __tablename__ = "close_approaches"

    des: Mapped[str] = mapped_column(Text, primary_key=True)
    orbit_id: Mapped[str] = mapped_column(Text, primary_key=True)
    close_approach_jd: Mapped[float] = mapped_column(Double, nullable=False)
    close_approach_time: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), primary_key=True
    )
    dist_au: Mapped[float | None] = mapped_column(Double, nullable=True)
    dist_min_au: Mapped[float | None] = mapped_column(Double, nullable=True)
    dist_max_au: Mapped[float | None] = mapped_column(Double, nullable=True)
    v_rel_kms: Mapped[float | None] = mapped_column(Double, nullable=True)
    v_inf_kms: Mapped[float | None] = mapped_column(Double, nullable=True)
    h_mag: Mapped[float | None] = mapped_column(Double, nullable=True)
    body: Mapped[str] = mapped_column(Text, nullable=False)
    ingested_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )

    __table_args__ = (
        Index("close_approaches_close_approach_time_idx", desc("close_approach_time")),
    )


class OrionEphemeris(Base):
    """JPL Horizons Orion spacecraft ephemeris record.

    Managed externally; Alembic now tracks schema but does not inject
    TimescaleDB hypertable operations.
    """

    __tablename__ = "orion_ephemeris"

    target_id: Mapped[str] = mapped_column(Text, primary_key=True)
    epoch: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), primary_key=True
    )
    jd: Mapped[float] = mapped_column(Double, nullable=False)
    x_km: Mapped[float | None] = mapped_column(Double, nullable=True)
    y_km: Mapped[float | None] = mapped_column(Double, nullable=True)
    z_km: Mapped[float | None] = mapped_column(Double, nullable=True)
    vx_kms: Mapped[float | None] = mapped_column(Double, nullable=True)
    vy_kms: Mapped[float | None] = mapped_column(Double, nullable=True)
    vz_kms: Mapped[float | None] = mapped_column(Double, nullable=True)
    speed_kms: Mapped[float | None] = mapped_column(Double, nullable=True)
    light_time_s: Mapped[float | None] = mapped_column(Double, nullable=True)
    range_km: Mapped[float | None] = mapped_column(Double, nullable=True)
    range_rate_kms: Mapped[float | None] = mapped_column(Double, nullable=True)
    ingested_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )

    __table_args__ = (
        Index("orion_ephemeris_epoch_idx", desc("epoch")),
    )


class DonkiEvent(Base):
    """NASA DONKI space weather event record.

    Managed externally; Alembic now tracks schema but does not inject
    TimescaleDB hypertable operations.
    """

    __tablename__ = "donki_events"

    event_type: Mapped[str] = mapped_column(Text, primary_key=True)
    event_id: Mapped[str] = mapped_column(Text, primary_key=True)
    start_time: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    end_time: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    event_time: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    fetched_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )
    source_url: Mapped[str] = mapped_column(Text, nullable=False)
    payload: Mapped[dict] = mapped_column(JSONB, nullable=False)

    __table_args__ = (
        Index("idx_donki_events_event_type_time", "event_type", "event_time"),
        Index("idx_donki_events_start_time", "start_time"),
    )


# ---- New real-data tables (NASA/CCMC/JPL managed, TimescaleDB hypertables) ----

class GoesIntegralProtons(Base):
    """NASA CCMC iSWA GOES integral proton flux (HAPI dataset goesp_part_flux_P5M).

    Managed externally; Alembic tracks schema and injects TimescaleDB hypertable operations.
    """

    __tablename__ = "goes_integral_protons"

    time: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), primary_key=True
    )
    proton_satellite: Mapped[str | None] = mapped_column(Text, nullable=True)
    p1_pfu: Mapped[float | None] = mapped_column(Double, nullable=True)
    p5_pfu: Mapped[float | None] = mapped_column(Double, nullable=True)
    p10_pfu: Mapped[float | None] = mapped_column(Double, nullable=True)
    p30_pfu: Mapped[float | None] = mapped_column(Double, nullable=True)
    p50_pfu: Mapped[float | None] = mapped_column(Double, nullable=True)
    p60_pfu: Mapped[float | None] = mapped_column(Double, nullable=True)
    p100_pfu: Mapped[float | None] = mapped_column(Double, nullable=True)
    p500_pfu: Mapped[float | None] = mapped_column(Double, nullable=True)
    ingested_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )

    __table_args__ = ()


class DsnSiteGeometry(Base):
    """JPL Horizons DSN site look angles for Orion spacecraft.

    Managed externally; Alembic tracks schema and injects TimescaleDB hypertable operations.
    """

    __tablename__ = "dsn_site_geometry"

    target_id: Mapped[str] = mapped_column(Text, primary_key=True)
    site: Mapped[str] = mapped_column(Text, primary_key=True)
    complex: Mapped[str] = mapped_column(Text, nullable=False)
    epoch: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), primary_key=True
    )
    azimuth_deg: Mapped[float | None] = mapped_column(Double, nullable=True)
    elevation_deg: Mapped[float | None] = mapped_column(Double, nullable=True)
    range_km: Mapped[float | None] = mapped_column(Double, nullable=True)
    range_rate_kms: Mapped[float | None] = mapped_column(Double, nullable=True)
    light_time_s: Mapped[float | None] = mapped_column(Double, nullable=True)
    visible: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
    ingested_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )

    __table_args__ = (
        Index("dsn_site_geometry_epoch_idx", desc("epoch")),
    )