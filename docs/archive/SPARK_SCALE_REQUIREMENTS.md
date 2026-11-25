# Uncertainty Quantification (Monte Carlo) & Spark Scale Requirements
 
> **Purpose**: Establish Monte Carlo uncertainty quantification as a core capability of the Artemis II Digital Twin, and document when (and whether) Apache Spark is needed to run it at scale.
> **Audience**: Engineers and stakeholders. Key concepts are explained in plain language.
> **Approach**: This document avoids precise sizing numbers. Real figures should come from measurement (profiling a single run, measuring actual data volumes), not advance estimates. What matters here is the *reasoning* and the *triggers*.
 
---
 
## 1. Why Monte Carlo Is a Priority
 
### The twin predicts; it does not observe
 
This digital twin computes spacecraft behavior **from physics, driven by planned inputs**: the nominal trajectory, the planned attitude timeline, planned maneuvers, assumed material and surface properties, and modeled environments. It does **not** have ground truth about what actually happened onboard. We have some data and a plan, not the real flight.
 
That has a direct consequence: **every input is an assumption, and every output inherits that uncertainty.** A single deterministic run produces one clean-looking answer, but that precision is false. Examples:
 
- The real attitude differs from the planned attitude (pointing errors, off-nominal holds, contingency changes).
- Maneuvers are never executed exactly as planned.
- Thermal coatings, contact conductances, and solar array performance differ from nominal values and drift over time.
- Solar flux, albedo, and radiation environment are forecasts or models, not measurements.
- The trajectory itself comes from a published estimate, not from the actual navigation solution.
So the honest question the twin should answer is not "what is the temperature of node 7?" but **"given what we know and do not know, what range of temperatures is plausible, and how likely is a limit violation?"** Monte Carlo is the standard tool for that question.
 
### What this changes about the project
 
- **Outputs become distributions, not single values.** Dashboards show nominal plus uncertainty bands.
- **Margins become probabilities.** "Probability a node exceeds its limit" or "probability state of charge dips below reserve in eclipse" replaces "the model says it stays within limits."
- **Sensitivity analysis becomes possible.** Sampling reveals which uncertain input drives each outcome, which tells us which assumptions matter and which do not.
- **Anomaly detection gets a defined baseline.** With no true telemetry to compare against, "anomalous" must mean "outside the plausible envelope predicted under uncertainty." The envelope is what makes an anomaly definition meaningful.
### Important honesty limits
 
- The ensemble captures only the uncertainty **we put in**. It shows plausible ranges *under stated assumptions*, not truth. Errors in the model structure itself (missing physics, wrong simplifications) are not captured by sampling parameters.
- Dashboards and reports should label results as "predicted range under assumed uncertainties," not as observed or verified behavior.
- If real telemetry or navigation updates ever become available, they should be used to **narrow the input distributions** (Bayesian updating or data assimilation), turning a prior-only twin into a calibrated one.
---
 
## 2. Plain-Language Concepts
 
### Monte Carlo Simulation
 
Imagine throwing darts blindfolded. You cannot predict any single dart, but many throws reveal the center, the spread, and the chance of a miss.
 
Here, each "throw" is a full simulation run with inputs sampled from assumed uncertainty distributions. The collection of results is a cloud of plausible outcomes.
 
```
Single deterministic run:   one line, one answer, false precision
Monte Carlo ensemble:       a band of plausible outcomes with probabilities
```
 
Cautions:
- Percentiles describe *dispersion*, not "best case / worst case."
- With nonlinear models, the ensemble median is not guaranteed to equal the nominal run.
### Two Ways Monte Carlo Appears in Physics Models
 
1. **Uncertainty propagation (wrapped around a model)**: keep the existing 0D/1D models and run them repeatedly with sampled inputs. This is the primary need for this project.
2. **Monte Carlo as the solution method**: some physics is computed by random sampling itself, such as particle-history radiation transport (Geant4/MCNP-style) and ray-traced radiative view factors for thermal coupling. These are specialized codes and a later extension.
### Embarrassingly Parallel
 
Each sample is independent and needs no communication with the others. Only the final aggregation (percentiles, probabilities, sensitivities) combines results. That independence is what makes ensembles easy to scale out when needed.
 
### Distributed Physics (CFD / FEM)
 
Lumped models use a handful of nodes per subsystem. 3D CFD/FEM resolves geometry finely to find local hot spots, thermal stress, and plume heating. Those solves are tightly coupled and belong to HPC solvers (MPI), not Spark.
 
---
 
## 3. Where Uncertainty Enters Each Contract
 
| Contract | Uncertain inputs (examples) | Uncertainty-aware output |
|----------|-----------------------------|--------------------------|
| 01_state_engine | Initial state, maneuver execution, navigation error, perturbation modeling | Trajectory dispersion tube; entry corridor and flyby miss-distance probabilities |
| 02_thermal_model | Attitude timeline errors, coating properties and degradation, contact conductances, solar/albedo flux | Temperature bands per node; probability of exceeding limits |
| 03_power_comms_radiation | Array degradation, pointing, load profiles, battery aging, radiation environment, shielding variation | State-of-charge bands, link margin probabilities, dose distributions |
| 04_cross_model_telemetry | Shared inputs across all models | Consistent joint outcomes (same sample drives every model) |
| 05_anomaly_ml_features | Baseline definition | Anomaly = outside predicted envelope, not outside a single line |
 
**Design principle:** a sample is defined once (trajectory, attitude, environment, and parameter draws) and fed to **all** coupled models. Otherwise cross-model results are physically inconsistent and joint risks are misestimated.
 
---
 
## 4. Architecture Requirements for the Uncertainty Layer
 
These hold regardless of whether Spark is ever used.
 
- **Sampling as a first-class component**: an explicit, versioned definition of each uncertain input (distribution, bounds, correlations, source and rationale for the assumption).
- **Correlated sampling**: correlated parameters are drawn jointly, not independently.
- **Reproducibility**: every run is identified by a seed and input-set version, so any sample can be recreated and audited.
- **Models as pure functions**: each model takes a sample and returns results, with no hidden shared state, so runs parallelize trivially.
- **Pluggable execution**: the same ensemble definition runs on one machine, a multi-core pool, a job scheduler, or Spark. Scaling out should be a change of executor, not a rewrite.
- **Convergence checks**: confirm statistics have stabilized, especially for rare-event tails.
- **Efficient sampling first**: stratified or Latin hypercube sampling, quasi-random sequences, variance reduction, importance sampling for tails, and surrogate models can cut the number of expensive runs needed more than extra hardware.
- **Compact outputs**: store summary envelopes, probabilities, and sensitivity indices for dashboards. Keep full per-run data only where deeper analysis needs it.
- **Honest labeling**: results are marked as predictions under stated assumptions.
---
 
## 5. What Spark Is and Is Not Good For
 
Spark is a **batch data-parallel engine**. It earns its place when:
- The ensemble or its result data outgrows a single machine, **and**
- The work splits into independent pieces that can be aggregated afterward.
It is a poor fit for:
- **Tightly coupled numerical solvers** (PDE solves need MPI and domain decomposition).
- **Very low-latency streaming** (micro-batching makes sub-second alerting a better fit for Flink or plain Kafka consumers).
- **Merely launching many independent jobs**, where a scheduler (Kubernetes jobs, Slurm, Argo, Airflow) is simpler.
**Monte Carlo being a priority does not make Spark a priority.** The capability is required; the platform is a separate decision made on evidence.
 
---
 
## 6. When Would Monte Carlo Justify Spark?
 
**Pushes toward Spark:**
- Many models multiplied by many samples multiplied by scenario sweeps (design variants, attitude timeline options, environment forecasts) creates a large job space even when each run is cheap.
- Coupled ensembles producing joint outcome data that must be analyzed together.
- Large retained result sets for sensitivity analysis, surrogate model training, or training anomaly detectors on simulated faults.
- Frequent reruns whenever the plan, attitude timeline, or environment forecast changes, requiring on-demand elastic capacity.
- Expensive individual runs (high-fidelity force models, long arcs, ray tracing).
**Argues against Spark:**
- Lumped models are cheap per run; a multi-core machine often covers a lot of ground.
- Heavy transport and 3D codes run best on dedicated HPC tooling, with at most a scheduler around them.
- Smarter sampling and surrogates reduce run counts.
**Rule:** start on one machine, measure per-run cost, ensemble size, and output volume against the required turnaround, and adopt a cluster only when a measured limit is hit.
 
---
 
## 7. Other Possible Extensions
 
### Multi-Mission Historical Analytics
Cross-mission lessons learned and larger ML training sets. Columnar tools (Polars, DuckDB over Parquet) handle very large archives on one machine for a long time. Spark is considered only when data or joins outgrow a single node. Avoid self-joining the full feature table (it grows quadratically); pivot by a shared key such as a mission-elapsed-time bucket instead.
 
### High-Fidelity Distributed Physics (3D CFD/FEM)
Tightly coupled, so the solves belong to MPI-based HPC solvers. Spark does not solve the PDEs. A scheduler (or Spark, if result data is large) can manage ensembles of 3D runs with varied configurations. Uncertainty here is typically handled with a *small, carefully chosen* set of expensive runs plus surrogates, not brute-force sampling.
 
### Monte Carlo as Solution Method (Radiation / Radiative Exchange)
Particle-history transport and ray-traced view factors are inherently Monte Carlo. Run them with dedicated codes on HPC or a scheduler. Spark would at most orchestrate and aggregate tallies.
 
### Real-Time Fleet Monitoring
Only relevant if the project grows to many spacecraft. Seconds-level latency is viable with Structured Streaming; tens-of-milliseconds targets favor Flink or lightweight consumers with a compact model.
 
---
 
## 8. Decision Criteria Summary
 
| Need | Try first | Consider Spark when... |
|------|-----------|------------------------|
| Monte Carlo over trajectory and physics models | Multi-core single machine, efficient sampling, surrogates | Measured runtime, memory, or result volume exceeds the required turnaround |
| Multi-mission analytics | Polars / DuckDB on Parquet | Data or joins no longer fit on one machine |
| 3D physics solves | HPC solvers (MPI) | Never for the solve; maybe for large result post-processing |
| Monte Carlo transport codes | Dedicated codes on HPC or scheduler | Rarely; orchestration and tally aggregation only |
| Fleet streaming | Kafka consumers / Flink | Latency target is seconds and logic is complex |
 
A requirement alone does not justify Spark. A requirement **plus** a measured limit on simpler tools does.
 
---
 
## 9. Recommended Phased Approach
 
```
Phases 1-13:   Deterministic single-mission twin, built so every model is a
               pure function of an explicit input set (sampling-ready)
     |
     v
Phase 14 (priority):  Uncertainty layer (Monte Carlo)
               - Input uncertainty definitions (attitude, maneuvers, environment,
                 material properties), with documented assumptions
               - Shared-sample ensembles across trajectory, thermal, power, radiation
               - Outputs: bands, limit-violation probabilities, sensitivities
               - Runs on one machine first; executor is swappable
     |
     v
Phase 15:      Scale-out decision gate
               - Measure; adopt Spark or a scheduler only if the ensemble needs it
               - Add surrogate models and tail-efficient sampling
     |
     v
Phase 16:      Calibration, if real data becomes available
               - Narrow input distributions from observations
     |
     v
Phase 17+:     Multi-mission analytics, 3D physics ensembles, and fleet streaming,
               each gated on funded requirement plus measured limits
```
 
Because the twin's honesty depends on uncertainty quantification, the *capability* belongs early. Making models sampling-ready costs little during Phases 1-13 and avoids rework.
 
---
 
## 10. If Spark Is Eventually Adopted
 
Keep sizing qualitative until a prototype provides measurements.
 
- **Cluster**: sized from profiled per-run cost and target turnaround; ephemeral, existing only for the batch.
- **Runtime**: managed Spark (Databricks, EMR) or Kubernetes with the Spark Operator, whichever the team already operates.
- **Schedule**: on demand when the plan or inputs change, or periodic. Never in the real-time path.
- **Input**: nominal trajectory, planned attitude timeline, and the versioned uncertainty definitions.
- **Output**: small summary tables for the dashboard, with optional full-ensemble Parquet.
- **Cost**: prototype runtime multiplied by cluster hourly price, compared against simply running longer on fewer machines.
Conceptual sketch:
```python
# Draw shared samples -> run all coupled models per sample -> aggregate
samples = spark.range(n_runs).rdd.map(draw_input_set)        # seeded, versioned
results = samples.mapPartitions(run_coupled_models)          # no shuffle
# Aggregation by time step does shuffle
summary = to_df(results).groupBy("met_seconds").agg(percentile_approx(...))
```
 
**Key principle:** Spark runs offline. The real-time pipeline stays simple.
 
---
 
## 11. Summary for Stakeholders
 
| Question | Answer |
|----------|--------|
| Why is Monte Carlo a priority? | The twin predicts from plans and assumptions without knowing what really happened, so single-run answers overstate certainty. |
| What does it deliver? | Plausible ranges, limit-violation probabilities, and sensitivity to assumptions. |
| What does it not deliver? | Truth. It reflects only the uncertainties we model, under stated assumptions. |
| Is Spark needed today? | No. Current workload is small and single-stream. |
| When is Spark justified? | When the Monte Carlo workload hits a measured limit of single-machine or scheduler-based execution. |
| Does Spark replace the current pipeline? | No. At most it adds a separate batch layer. |
| What if the ensembles stay small? | Never install Spark. The capability is delivered without it. |
 
---
 
## 12. Glossary
 
| Term | Definition |
|------|------------|
| **Monte Carlo** | Running a simulation many times with randomized inputs to understand uncertainty |
| **Uncertainty propagation** | Pushing input uncertainty through a model to see the resulting output uncertainty |
| **Covariance matrix** | Describes how uncertain each input is and how uncertainties correlate |
| **Percentile envelope** | Bounds on dispersion (e.g., 5th to 95th percentile) across runs; not "best/worst case" |
| **3-sigma** | Roughly 99.7% of outcomes for a normal distribution |
| **Sensitivity analysis** | Determining which uncertain inputs most affect an output |
| **Surrogate model** | A fast statistical approximation of an expensive model, trained on a limited set of runs |
| **Importance sampling** | Sampling technique for estimating rare-event probabilities with far fewer samples |
| **Data assimilation** | Updating model inputs or states using observations to reduce uncertainty |
| **Embarrassingly parallel** | Work that splits into independent pieces needing no communication |
| **CFD / FEM** | 3D flow/heat and structural/thermal simulation methods |
| **Domain decomposition** | Splitting a 3D mesh across processors that exchange boundary data each step |
| **MPI** | Message Passing Interface: standard for communication between HPC processes |
| **Structured Streaming** | Spark's micro-batch streaming engine with event-time processing |
 
---
 
## 13. Next Steps
 
1. Confirm Monte Carlo uncertainty quantification as a core requirement, and the confidence levels stakeholders care about.
2. Build the input uncertainty register: each uncertain input, its distribution, correlations, and the source of the assumption.
3. Make existing models sampling-ready (pure functions of an explicit input set, seeded, versioned).
4. Prototype a shared-sample ensemble locally with a small number of runs. Measure per-run cost and output size.
5. Decide on scale-out (Spark or scheduler) only if measurements show single-machine execution is inadequate. Otherwise record "Spark not required" in an ADR.
6. Define how results are labeled and how real data, if it appears, will update the input distributions.
7. Revisit at each phase gate.
