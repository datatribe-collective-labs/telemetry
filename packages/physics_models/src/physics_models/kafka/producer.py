"""Kafka producer for physics models."""

from typing import Any

from confluent_kafka import Producer
from contracts import (
    SyntheticAnomalyEvent,
    SyntheticCommsOutput,
    SyntheticCrossModelState,
    SyntheticMLFeatureVector,
    SyntheticPowerOutput,
    SyntheticRadiationOutput,
    SyntheticStateSnapshot,
    SyntheticTelemetryPacket,
    SyntheticThermalOutput,
)


class Topics:
    TRAJECTORY = "trajectory"
    TELEMETRY = "telemetry"
    CROSS_MODEL_STATE = "cross_model_state"
    EVENTS = "events"
    ML_FEATURES = "ml_features"


class PhysicsModelsKafkaProducer:
    """Async batched Kafka producer with backpressure handling."""

    def __init__(self, bootstrap_servers: str):
        self._producer = Producer({
            "bootstrap.servers": bootstrap_servers,
            "linger.ms": 5,
            "batch.size": 65536,
            "compression.type": "zstd",
            "max.in.flight.requests.per.connection": 5,
            "acks": "all",
        })

    def send_state(self, msg: SyntheticStateSnapshot) -> None:
        self._produce(Topics.TRAJECTORY, msg.timestamp_utc.isoformat(), msg)

    def send_thermal(self, msg: SyntheticThermalOutput) -> None:
        self._produce(Topics.TELEMETRY, msg.timestamp_utc.isoformat(), msg)

    def send_power(self, msg: SyntheticPowerOutput) -> None:
        self._produce(Topics.TELEMETRY, msg.timestamp_utc.isoformat(), msg)

    def send_comms(self, msg: SyntheticCommsOutput) -> None:
        self._produce(Topics.TELEMETRY, msg.timestamp_utc.isoformat(), msg)

    def send_radiation(self, msg: SyntheticRadiationOutput) -> None:
        self._produce(Topics.TELEMETRY, msg.timestamp_utc.isoformat(), msg)

    def send_cross_model(self, msg: SyntheticCrossModelState) -> None:
        self._produce(Topics.CROSS_MODEL_STATE, msg.timestamp_utc.isoformat(), msg)

    def send_packet(self, msg: SyntheticTelemetryPacket) -> None:
        self._produce(Topics.TELEMETRY, msg.timestamp_utc.isoformat(), msg)

    def send_anomaly(self, msg: SyntheticAnomalyEvent) -> None:
        self._produce(Topics.EVENTS, msg.event_id, msg)

    def send_ml_features(self, msg: SyntheticMLFeatureVector) -> None:
        self._produce(Topics.ML_FEATURES, msg.timestamp_utc.isoformat(), msg)

    def _produce(self, topic: str, key: str, msg: Any) -> None:
        self._producer.produce(
            topic,
            key=key.encode(),
            value=msg.model_dump_json().encode(),
            headers=[("schema_version", b"1")],
        )

    def flush(self, timeout: float = 5.0) -> None:
        self._producer.flush(timeout)

    def poll(self, timeout: float = 0.0) -> None:
        self._producer.poll(timeout)