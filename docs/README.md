# Telemetry Project Documentation

Start here. Docs are grouped by **type** — find the folder, then the file.
For *running* the services, see the root [`RUN_SERVICES.md`](../RUN_SERVICES.md). For how **real data** (NASA/JPL) and **synthetic data** (physics models) fit together, see "Real data vs synthetic data" in the root [`README.md`](../README.md).

## Overview — *"What is this project and how does it fit together?"*

| Doc / file | Read this when… |
|-----|-----------------|
| [ARCHITECTURE.md](ARCHITECTURE.md) | You need the big picture: the parts, how real and synthetic data flow through them, sources, Kafka topics, tables, routes and repo layout. Start here. |
| `../data/oem/all-artemis-ii-oem-files.zip` | **NASA source data** — 10 CCSDS OEM v2.0 ephemeris arcs (EME2000, UTC, 240 s cadence) for the state engine and trajectory dashboard. Ingested into `oem_state_vectors` by `pipelines.ingest.nasa_oem`. |

## Architecture — *"How is it designed?"*

| Doc | Read this when… |
|-----|-----------------|
| [architecture/PHYSICS_MODELS.md](architecture/PHYSICS_MODELS.md) | You're working in `packages/physics_models/` — the tick loop, the five models, one-tick-lag coupling, tick validation, Kafka publishing, replay settings. Anomaly and ML are placeholders. |
| [architecture/DASHBOARD.md](architecture/DASHBOARD.md) | You're changing the Digital Twin dashboard (`dashboard/src/prototype/`) — pages, data flow from the backend, live/replay, source badges, design decisions. |

## Integration — *"Does the output meet the contracts?"*

| Doc | Read this when… |
|-----|-----------------|
| [integration/CONTRACT_COMPLIANCE.md](integration/CONTRACT_COMPLIANCE.md) | You want to know how well each physics model meets its ODCS contract: status per contract, how the rules are enforced, known deviations. |

## Guides — *"How do I do X?"*

| Doc | Read this when… |
|-----|-----------------|
| [guides/UPCLOUD_DEPLOYMENT.md](guides/UPCLOUD_DEPLOYMENT.md) | You're putting the demo on a server: the UpCloud runbook (server, firewall, database, `.env`, first deploy, operations, recovery, shutdown). |
| [guides/MONITORING.md](guides/MONITORING.md) | You're setting up or answering the demo's alerts: Grafana ops dashboard and email alerts, the host check (healthchecks.io), what to do when an alert arrives, planned restarts, drills. |

## Decisions — *"Why did we choose X?"*

| Doc | Read this when… |
|-----|-----------------|
| [decisions/ONE_DASHBOARD.md](decisions/ONE_DASHBOARD.md) | You wonder why there is one dashboard, not a separate real-data Data Explorer, and what happened to its pages (#32). |
| [decisions/SPARK_SCALE_REQUIREMENTS.md](decisions/SPARK_SCALE_REQUIREMENTS.md) | You're questioning whether/when Apache Spark is needed (Monte Carlo uncertainty quantification). |
| [decisions/REDPANDA.md](decisions/REDPANDA.md) | You wonder why the Kafka broker is Redpanda, and why messages are kept for only an hour. |
| [decisions/MANAGED_POSTGRESQL.md](decisions/MANAGED_POSTGRESQL.md) | You wonder why the public server uses UpCloud Managed PostgreSQL instead of the database container. |
| [decisions/MONITORING.md](decisions/MONITORING.md) | You wonder how the demo is monitored (Grafana alerts + host check with healthchecks.io) and what was rejected. |

## Archive — *"How did we get here?"*

[archive/](archive/README.md) keeps historical documents (a debugging record, the timeline fact-check checklist, the SGPS flux derivation, the full Spark analysis). Not maintained.

## Other repo docs (not in this folder)

- [`../README.md`](../README.md) — project quickstart
- [`../RUN_SERVICES.md`](../RUN_SERVICES.md) — service startup order & troubleshooting
- [`../CLAUDE.md`](../CLAUDE.md) — agent guidance for working in this repo
- `packages/*/README.md`, `dashboard/README.md` — per-package docs (backend API reference: `packages/backend/src/backend/api/README.md`)
