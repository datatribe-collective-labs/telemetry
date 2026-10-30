"""Configuration for physics models."""

from pathlib import Path

from pydantic import BaseModel, Field


class KafkaConfig(BaseModel):
    bootstrap_servers: str = "kafka:9092"
    topics: dict[str, str] = Field(default_factory=lambda: {
        "trajectory": "trajectory",
        "telemetry": "telemetry",
        "cross_model_state": "cross_model_state",
        "events": "events",
        "ml_features": "ml_features",
    })


class StateEngineConfig(BaseModel):
    oem_source: str = "oem_store"  # "oem_store" (zip of zips), "oem_file" (.asc), or "placeholder"
    oem_store_path: str | None = "data/oem/all-artemis-ii-oem-files.zip"
    oem_file_path: str | None = None  # direct path to a .asc (overrides store)
    liftoff_utc: str = "2026-04-01T22:35:00Z"
    tick_hz: float = 1.0


class ThermalNodeConfig(BaseModel):
    C: float = 20000.0   # J/K
    A: float = 4.0       # m^2
    eps: float = 0.85
    alpha: float = 0.92


class ThermalConfig(BaseModel):
    tick_hz: float = 1.0
    sun_face: ThermalNodeConfig = Field(default_factory=lambda: ThermalNodeConfig(C=20000.0, A=4.0, eps=0.85, alpha=0.92))
    shadow_face: ThermalNodeConfig = Field(default_factory=lambda: ThermalNodeConfig(C=20000.0, A=4.0, eps=0.80, alpha=0.15))
    electronics_bay: ThermalNodeConfig = Field(default_factory=lambda: ThermalNodeConfig(C=80000.0, A=0.2, eps=0.85, alpha=0.3))
    K_sun_shadow: float = 0.2   # W/K
    K_sun_elec: float = 0.2
    K_shadow_elec: float = 0.3
    heater_power_w: float = 25.0
    heater_setpoint_k: float = 268.15  # -5 C, per contract 02
    heater_deadband_k: float = 2.0
    bay_heat_fraction: float = 0.30  # fraction of electrical load dissipated as bay heat
    # (avionics realistic range; MODEL_ASSUMPTION — no public Orion EPS budget)


class PowerConfig(BaseModel):
    tick_hz: float = 1.0


class CommsConfig(BaseModel):
    tick_hz: float = 1.0


class RadiationConfig(BaseModel):
    tick_hz: float = 1.0


class AnomalyConfig(BaseModel):
    detection_layer_1_enabled: bool = True
    detection_layer_2_enabled: bool = True
    ml_enabled: bool = True


class MLFeaturesConfig(BaseModel):
    tick_hz: float = 1.0


class PhysicsModelsConfig(BaseModel):
    tick_hz: float = 1.0
    time_scale: float = 1.0
    """Simulation speed multiplier vs wall clock (1.0 = real-time, 600 = 10 min sim per wall-second)."""
    start_met_seconds: float = 0.0
    """Seek: simulation clock starts this many seconds after liftoff (e.g. 92620 ≈ TLI)."""
    kafka: KafkaConfig = Field(default_factory=KafkaConfig)
    state_engine: StateEngineConfig = Field(default_factory=StateEngineConfig)
    thermal: ThermalConfig = Field(default_factory=ThermalConfig)
    power: PowerConfig = Field(default_factory=PowerConfig)
    comms: CommsConfig = Field(default_factory=CommsConfig)
    radiation: RadiationConfig = Field(default_factory=RadiationConfig)
    anomaly: AnomalyConfig = Field(default_factory=AnomalyConfig)
    ml_features: MLFeaturesConfig = Field(default_factory=MLFeaturesConfig)


def load_config(path: str | Path) -> PhysicsModelsConfig:
    """Load configuration from YAML file."""
    import yaml
    with open(path) as f:
        data = yaml.safe_load(f)
    return PhysicsModelsConfig(**data)