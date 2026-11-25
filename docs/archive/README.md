# Archive

Historical documents, kept as a record of how the project was built. They describe the
code as it was when they were written: paths, status notes and open tasks in them may be
out of date, and nothing here is maintained. For the project as it is now, start at the
[documentation index](../README.md).

All four were written by Eveliina Vesala.

| Doc | What it records |
|-----|-----------------|
| [DEBUG_DOCKER_PHYSICS_MODELS.md](DEBUG_DOCKER_PHYSICS_MODELS.md) | Debugging the physics models container that hung at start-up (asyncio signal handling); fixed on 2026-10-19 |
| [TIMELINE_FACTCHECK_CHECKLIST.md](TIMELINE_FACTCHECK_CHECKLIST.md) | The checklist for verifying the extracted mission timeline (`contracts.planned_attitude`) against NASA's Overview Timeline PDF |
| [sgps_ge10_proton_flux.md](sgps_ge10_proton_flux.md) | Deriving the >=10 MeV proton flux from GOES SGPS channels. The transform it describes was never used by an ingest job and was removed; the GOES data comes from NOAA's integral product via iSWA (`pipelines.ingest.iswa_goes_protons`) |
| [SPARK_SCALE_REQUIREMENTS.md](SPARK_SCALE_REQUIREMENTS.md) | The full analysis of Monte Carlo uncertainty quantification and when Apache Spark would be needed; the decision is summarized in [`decisions/SPARK_SCALE_REQUIREMENTS.md`](../decisions/SPARK_SCALE_REQUIREMENTS.md) |
