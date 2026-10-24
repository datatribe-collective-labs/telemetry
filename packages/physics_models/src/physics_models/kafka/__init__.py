"""Kafka integration for physics models."""

from physics_models.kafka.producer import PhysicsModelsKafkaProducer, Topics

__all__ = [
    "PhysicsModelsKafkaProducer",
    "Topics",
]