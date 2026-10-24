# Telemetry Project Documentation

Start here. Docs are grouped by **type** — find the folder, then the file.
For *running* the services, see the root [`RUN_SERVICES.md`](../RUN_SERVICES.md).

## Overview — *"What is this project and where is it going?"*

| Doc / file | Read this when… |
|-----|-----------------|
| [overview/PROJECT_OVERVIEW.md](overview/PROJECT_OVERVIEW.md) | You need the big picture: mission, tech stack, component status, project structure, startup order, next steps. The main project handbook. |
| [overview/DATA_SOURCE_ANALYSIS.md](overview/DATA_SOURCE_ANALYSIS.md) | You're adding or evaluating data sources — current sources, their contracts, and what's missing. |
| `../data/oem/all-artemis-ii-oem-files.zip` | **NASA source data** — 10 CCSDS OEM v2.0 ephemeris arcs (EME2000, UTC, 240 s cadence) for the state engine and trajectory dashboard. Ingested into `oem_state_vectors` by `pipelines.ingest.nasa_oem`. Facts transcribed in `guides/ARTEMIS_II_RESEARCH_QUESTIONS.md`. |
| `overview/artemis-ii-overview-timeline-public-final.pdf` | Official Artemis II event timeline (ICPS sep, TLI, lunar close approach, splashdown METs) — source of the mission event table. |
| `overview/sls-5558-artemis-ii-sls-reference-guide.pdf` | SLS Reference Guide — contract 02's source for the 249–310 K electronics reference range. |

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
| [integration/CONTRACT_PHYSICS_AUDIT.md](integration/CONTRACT_PHYSICS_AUDIT.md) | You want the physics sanity check of the contracts + the audit of what the owned models (state/thermal/power) actually do at runtime — incl. the "runner emits placeholders" finding. |
| [integration/sgps_ge10_proton_flux.md](integration/sgps_ge10_proton_flux.md) | You're touching the GOES proton flux ingest (`iswa_goes_protons`) — SGPS → ≥10 MeV flux derivation details. |

## Guides — *"How do I do X?"*

| Doc | Read this when… |
|-----|-----------------|
| [guides/orion-testing-walkthrough.md](guides/orion-testing-walkthrough.md) | You're reviewing/test-running the JPL Horizons Orion datasource end to end. |
| [guides/PROMPT_PDF_ATTITUDE_PARSING.md](guides/PROMPT_PDF_ATTITUDE_PARSING.md) | You're re-parsing the Artemis II attitude profile PDF into structured data (`planned_attitude.py` inputs). |
| [guides/TIMELINE_FACTCHECK_CHECKLIST.md](guides/TIMELINE_FACTCHECK_CHECKLIST.md) | **Manual task:** verify all 108 extracted attitude segments against the timeline PDF — generated mechanically from the code, with anchors and known gaps already flagged. |
| [guides/DEBUG_DOCKER_PHYSICS_MODELS.md](guides/DEBUG_DOCKER_PHYSICS_MODELS.md) | Historical record of the Docker asyncio/signal hang — **resolved 2026-10-19**; keep for debugging technique reference only. |
| [guides/ARTEMIS_II_RESEARCH_QUESTIONS.md](guides/ARTEMIS_II_RESEARCH_QUESTIONS.md) | You need to (re)collect external Artemis II facts — copy-paste prompt for ChatGPT: flight profile, EPS, comms, thermal, contract sanity checks. Paste answers back into this file. |

## Decisions — *"Why did we choose X?"*

| Doc | Read this when… |
|-----|-----------------|
| [decisions/testing-infrastructure-plan.md](decisions/testing-infrastructure-plan.md) | You're changing the test setup (pytest layout, docker `tests` service, DB fixtures). |
| [decisions/SPARK_SCALE_REQUIREMENTS.md](decisions/SPARK_SCALE_REQUIREMENTS.md) | You're questioning whether/when Apache Spark is needed (Monte Carlo uncertainty quantification). |

## Other repo docs (not in this folder)

- [`../README.md`](../README.md) — project quickstart
- [`../RUN_SERVICES.md`](../RUN_SERVICES.md) — service startup order & troubleshooting
- [`../CLAUDE.md`](../CLAUDE.md) — agent guidance for working in this repo
- [`../GIT_COMMIT_PLAN.md`](../GIT_COMMIT_PLAN.md) — commit hygiene & secrets policy
- `packages/*/README.md` — per-package docs (backend API reference: `packages/backend/src/backend/api/README.md`)
