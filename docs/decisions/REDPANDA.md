# Redpanda as the Kafka broker

> **Status:** accepted. Redpanda came in with the synthetic data path (#25). The reasons
> were not written down at the time; this record describes what the choice gives the
> project as it runs now.

## Context

The simulator publishes every tick's outputs as messages, and a separate consumer writes
them to the database. That needs a broker that speaks the Kafka protocol, so standard
clients (`confluent_kafka`) and Kafka tools work. The whole stack runs on one laptop or
one small server, next to TimescaleDB, Airflow and the app.

## Decision

Run **Redpanda** (a Kafka-compatible broker) as one container instead of Apache Kafka:

- one process, with no ZooKeeper or separate controller to run,
- a fixed memory budget (`--memory=1G`, one core),
- the Kafka API, so the producer and consumer code is plain Kafka code.

Messages are kept for **1 hour** (`redpanda.log_retention_ms`), not the 7-day default
(#64). The consumer reads them live, and the database is the record.

## Consequences

- Switching to Apache Kafka or a managed Kafka service later only changes the
  `KAFKA_BOOTSTRAP_SERVERS` address and the compose service, not the code.
- Redpanda has no volume: messages that are not consumed within the hour, or when the
  container is recreated, are lost. That is acceptable because the simulator can replay the
  mission at any time and the consumer upserts on `timestamp_utc`.
- The real-data path does not use Kafka. Its batch ingest jobs write straight to the
  database.
