# Telemetry Project Documentation

Start here. Docs are grouped by **type** — find the folder, then the file.
For *running* the services, see the root [`RUN_SERVICES.md`](../RUN_SERVICES.md).

## Overview — *"What is this project and where is it going?"*

| Doc / file | Read this when… |
|-----|-----------------|
| [overview/PROJECT_OVERVIEW.md](overview/PROJECT_OVERVIEW.md) | You need the big picture: mission, tech stack, component status, project structure, startup order, next steps. The main project handbook. |
| `../data/oem/all-artemis-ii-oem-files.zip` | **NASA source data** — 10 CCSDS OEM v2.0 ephemeris arcs (EME2000, UTC, 240 s cadence) for the state engine and trajectory dashboard. Ingested into `oem_state_vectors` by `pipelines.ingest.nasa_oem`. |

## Architecture — *"How is it designed?"*

| Doc | Read this when… |
|-----|-----------------|
| [architecture/PHYSICS_MODELS_ARCHITECTURE.md](architecture/PHYSICS_MODELS_ARCHITECTURE.md) | You're working in `packages/physics_models/` — package layout, tick loop, cross-model coupling, Kafka producer design. **Note: this is the target architecture**; comms/radiation/packet/anomaly are not yet implemented (banner at top of file). |
| [architecture/DASHBOARD_ARCHITECTURE.md](architecture/DASHBOARD_ARCHITECTURE.md) | You're building or changing dashboards — three tiers (pipeline explorer / Streamlit prototype / future production JS), page designs, which backend endpoints feed which widgets. |
| [architecture/DASHBOARD_V1_DESIGN.md](architecture/DASHBOARD_V1_DESIGN.md) | You're building the **v1 Streamlit prototype** (`dashboard/src/prototype/`) — page-by-page plan, flyby visualization, data organization, build order. |

## Integration — *"Is the pipeline wired up correctly?"*

| Doc | Read this when… |
|-----|-----------------|
| [integration/PIPELINE_STATUS.md](integration/PIPELINE_STATUS.md) | You want the verified end-to-end status (contracts → Kafka → consumer → TimescaleDB → backend → dashboard), verification commands, and known gaps. |
| [integration/PHYSICS_MODELS_CONTRACT_COMPLIANCE.md](integration/PHYSICS_MODELS_CONTRACT_COMPLIANCE.md) | You're implementing a physics model and need its ODCS contract field-by-field: quality rules, bounds, compliance status per model. |
| [integration/sgps_ge10_proton_flux.md](integration/sgps_ge10_proton_flux.md) | You're touching the GOES proton flux ingest (`iswa_goes_protons`) — SGPS → ≥10 MeV flux derivation details. |

## Guides — *"How do I do X?"*

| Doc | Read this when… |
|-----|-----------------|
| [guides/TIMELINE_FACTCHECK_CHECKLIST.md](guides/TIMELINE_FACTCHECK_CHECKLIST.md) | **Manual task:** verify all 108 extracted attitude segments against the timeline PDF — generated mechanically from the code, with anchors and known gaps already flagged. |
| [guides/DEBUG_DOCKER_PHYSICS_MODELS.md](guides/DEBUG_DOCKER_PHYSICS_MODELS.md) | Historical record of the Docker asyncio/signal hang — **resolved 2026-10-19**; keep for debugging technique reference only. |

## Decisions — *"Why did we choose X?"*

| Doc | Read this when… |
|-----|-----------------|
| [decisions/SPARK_SCALE_REQUIREMENTS.md](decisions/SPARK_SCALE_REQUIREMENTS.md) | You're questioning whether/when Apache Spark is needed (Monte Carlo uncertainty quantification). |

## Other repo docs (not in this folder)

- [`../README.md`](../README.md) — project quickstart
- [`../RUN_SERVICES.md`](../RUN_SERVICES.md) — service startup order & troubleshooting
- [`../CLAUDE.md`](../CLAUDE.md) — agent guidance for working in this repo
- `packages/*/README.md`, `dashboard/README.md` — per-package docs (backend API reference: `packages/backend/src/backend/api/README.md`)
