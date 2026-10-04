# Spark Scale Requirements: Monte Carlo & Distributed Physics

> **Purpose**: Document where Apache Spark is genuinely justified in the Artemis II Digital Twin project.
> **Audience**: Engineers and stakeholders — includes plain-language explanations of key concepts.

---

## 1. Plain-Language Concept Explanations

### What is Monte Carlo Simulation?

**Analogy**: Imagine you're throwing darts at a dartboard while blindfolded. You don't know exactly where each dart will land, but you know roughly where you're aiming. If you throw **10,000 darts**, the pattern of where they hit tells you:
- Where the *center* of your throws is (most likely outcome)
- How *wide* the spread is (uncertainty)
- The chance of hitting the bullseye vs. missing the board entirely (risk)

**In our context**: Instead of darts, we're simulating Artemis II's trajectory. We don't know the *exact* initial position/velocity — JPL Horizons gives us a best estimate ± uncertainty. Monte Carlo runs the trajectory **thousands of times** with slightly different starting conditions (sampled from the uncertainty distribution). The result is a **probability cloud** of where Orion might be at any given time.

```
Single deterministic run:     One line through space
Monte Carlo (10,000 runs):    A "tube" or cloud showing probable positions
                               ├── 5th percentile (worst case)
                               ├── 50th percentile (most likely)  ← nominal trajectory
                               └── 95th percentile (best case)
```

**Why it matters for Artemis II**:
- **Collision avoidance**: What's the probability we hit debris?
- **Entry corridor**: Will we hit the narrow entry window at Earth return?
- **Fuel margins**: How much extra ΔV do we need for 99% mission success?
- **Communication**: When might we lose DSN contact due to trajectory dispersion?

---

### What is Distributed Physics (CFD/FEM)?

**Current approach (0D/1D models)**: Treat the spacecraft as a few "lumped" nodes.
- Thermal: 10-50 nodes (each = a whole panel or compartment)
- Power: 1 battery, 2 solar array wings, 1 bus
- Radiation: 1 dose point behind shielding

**Distributed physics (3D CFD/FEM)**:
- **CFD** (Computational Fluid Dynamics): Simulate gas flow, heat transfer in 3D
- **FEM** (Finite Element Method): Simulate structural stress, thermal conduction in 3D mesh

```
0D Model (current):           3D FEM/CFD (distributed):
┌─────────┐                   ┌─────────────────┐
│  Box    │                   │  1,000,000      │
│  "Node" │                   │  tetrahedral    │
└─────────┘                   │  elements       │
                              └─────────────────┘
     1 temperature                1M temperatures
     1 heat flow            →     3M heat flows
                                (per timestep)
```

**Why it matters**:
- **Hot spots**: 0D model averages; FEM finds local overheating on a bracket
- **Thermal stress**: CFD/FEM predicts material fatigue from thermal cycling
- **Plume impingement**: RCS thruster plumes heating specific surfaces
- **Radiation transport**: 3D shielding analysis (not just "aluminum equivalent")

---

### What is "Embarrassingly Parallel"?

A task where **each piece is completely independent** — no communication needed between pieces.

```
Monte Carlo trajectory:     Run 1    Run 2    Run 3    ...    Run 10,000
                            ↓        ↓        ↓               ↓
                         Worker 1  Worker 2  Worker 3    Worker N
                            ↓        ↓        ↓               ↓
                         Result 1  Result 2  Result 3    Result N
                            └────────┴────────┴────────┴──────┘
                                         ↓
                              Aggregate (percentiles, stats)
```

**Perfect for Spark**: Each worker gets a batch of initial conditions, runs propagation independently, returns results. No shuffling, no synchronization.

---

## 2. Where These Fit in Our Architecture

### Current Contracts (Deterministic, Single-Run)

| Contract | Scope | Scale |
|----------|-------|-------|
| 01_state_engine | One trajectory (ID `-1024`) | ~1,440 points/day |
| 02_thermal_model | 0D lumped-parameter | ~50 nodes |
| 03_power_comms_radiation | 0D/1D models | ~15 nodes |
| 04_cross_model_telemetry | Single packet stream | 1 Hz |
| 05_anomaly_ml_features | One stream | 86,400 packets/day |

**Spark needed?** ❌ No — single-node Python + TimescaleDB handles this easily.

---

### Proposed Extensions (Where Spark Shines)

#### Extension A: Monte Carlo Trajectory Ensembles (Contract 01+)

| Aspect | Deterministic (Current) | Monte Carlo (Extension) |
|--------|------------------------|-------------------------|
| **Input** | 1 state vector | 10,000 state vectors (sampled from covariance) |
| **Propagation** | 1 run | 10,000 independent runs |
| **Output** | 1 position/time | 10,000 positions/time → percentiles |
| **Storage** | ~1 MB/day | ~50 TB for full ensemble (compressed: ~5 TB) |
| **Compute** | 1 CPU-second | 10,000 CPU-hours (or 1 hour on 10,000 cores) |
| **Spark Role** | Not used | **Distribute runs, aggregate percentiles** |

**Trigger**: Mission design review needs "3-sigma dispersion at lunar flyby"

**Implementation**:
```python
# spark_jobs/monte_carlo_trajectory.py
def run_ensemble(num_runs=10000, mission_days=10):
    # 1. Sample initial conditions from JPL covariance matrix
    samples = spark.range(num_runs).map(sample_initial_state)
    
    # 2. Propagate each trajectory (embarrassingly parallel)
    trajectories = samples.mapPartitions(propagate_batch)
    
    # 3. Compute statistical envelopes per MET timestep
    envelopes = trajectories.groupBy("met_seconds").agg(
        percentile_approx("x_km", [0.001, 0.01, 0.05, 0.25, 0.5, 0.75, 0.95, 0.99, 0.999]),
        percentile_approx("y_km", [...]),
        percentile_approx("z_km", [...]),
        percentile_approx("vx_kms", [...]),
        ...
    )
    
    # 4. Store envelopes (small: 1 row per MET second × 50 stats)
    envelopes.write.jdbc(timescale_url, "mc_trajectory_envelopes")
    
    # 5. Optionally store full ensemble for deep-dive (Parquet to S3)
    trajectories.write.parquet("s3://artemis-mc/trajectories/")
```

**Dashboard use**: Show "uncertainty tubes" around nominal trajectory.

---

#### Extension B: Multi-Mission Historical Replay (New Contract 06)

| Aspect | Single Mission | 50 Missions × 10 Years |
|--------|----------------|------------------------|
| **Telemetry rows** | 30M/year | 1.5B/year |
| **Anomaly correlation** | Within mission | Cross-mission patterns |
| **ML training data** | 1 mission | Fleet-wide |
| **Spark Role** | Not used | **ETL, feature engineering, distributed training** |

**Trigger**: NASA wants "lessons learned across Artemis I-V, Orion, Gateway, Commercial"

**Implementation**:
```python
# spark_jobs/fleet_feature_engineering.py
# Join telemetry across missions, compute cross-mission features
telemetry = spark.read.parquet("s3://artemis-telemetry/*/")

# Rolling window features per spacecraft
features = telemetry.groupBy("spacecraft_id", "met_bucket").agg(
    mean("temp_node_1"), stddev("temp_node_1"),
    min("battery_soc"), max("battery_soc"),
    ...
)

# Cross-mission: "How did Artemis II thermal compare to Artemis I at same MET?"
cross_mission = features.join(features.alias("other"), 
    (col("met_bucket") == col("other.met_bucket")) & 
    (col("spacecraft_id") != col("other.spacecraft_id")))
```

---

#### Extension C: High-Fidelity Distributed Physics (Contract 02/03 Extension)

| Model | Current (0D) | Distributed (3D FEM/CFD) |
|-------|--------------|--------------------------|
| **Thermal nodes** | 50 | 1,000,000 |
| **Timestep** | 1-10 sec | 0.001-0.1 sec (explicit) |
| **Per-run compute** | 0.1 CPU-sec | 10,000 CPU-hours |
| **Use case** | System-level trends | Hot spots, stress, plume heating |
| **Spark Role** | Not used | **Mesh partitioning, distributed linear solve** |

**Note**: True CFD/FEM needs **MPI + domain decomposition**, not Spark. But Spark can:
- Manage ensemble of 3D runs (different configs)
- Pre/post-process mesh data (partitioning, boundary conditions)
- Aggregate results across runs

**Better tool for 3D physics**: **Dask + MPI**, or dedicated HPC (OpenFOAM, NASTRAN, ANSYS). Spark is for the *ensemble management*, not the PDE solve.

---

#### Extension D: Real-Time Fleet Monitoring (Contract 05 Extension)

| Aspect | Single Stream | 1,000 Spacecraft |
|--------|---------------|------------------|
| **Ingest rate** | 1 Hz | 10,000 Hz |
| **Anomaly latency** | 1 sec | < 100 ms |
| **Spark Role** | Not used | **Structured Streaming + ML inference** |

```python
# spark_streaming/anomaly_detection.py
stream = spark.readStream.kafka("telemetry-fleet")

# Per-spacecraft rolling features
features = stream.groupBy("spacecraft_id", window("timestamp", "10 sec")).agg(
    mean("temp"), stddev("temp"),
    mean("current"), stddev("current"),
    ...
)

# ML inference (broadcast model)
predictions = features.mapInPandas(apply_onnx_model, schema)

# Alert on anomalies
predictions.filter("anomaly_score > 0.95").writeStream.kafka("alerts")
```

---

## 3. Decision Matrix: When to Introduce Spark

| Requirement | Current Plan | Add Spark When... |
|-------------|--------------|-------------------|
| **Single-mission deterministic sim** | Python + TimescaleDB | Never |
| **Monte Carlo ensembles** | Not planned | Phase 14+ (design review needs uncertainty) |
| **Multi-mission fleet** | Not planned | Phase 15+ (Artemis III+ operational) |
| **3D FEM/CFD physics** | 0D models only | Phase 16+ (hot spot analysis required) |
| **Real-time fleet streaming** | Single stream | Phase 17+ (Gateway/CLPS fleet) |
| **Petabyte ML feature store** | Parquet + Polars | Phase 18+ (100+ TB training data) |

---

## 4. Recommended Phased Approach

```
Phase 1-13 (Current):     Deterministic single-mission digital twin
     │
     ▼
Phase 14:                 Monte Carlo batch layer (Spark)
     │  • 10K trajectory runs for uncertainty quantification
     │  • Output: percentile envelopes → TimescaleDB for dashboard
     │  • Runs weekly, not real-time
     │
     ▼
Phase 15:                 Multi-mission analytics (Spark)
     │  • Cross-mission anomaly correlation
     │  • Fleet-wide ML feature engineering
     │
     ▼
Phase 16:                 Distributed physics management (Spark + MPI)
     │  • Manage ensembles of 3D thermal/structural runs
     │  • Spark orchestrates; MPI does the PDE solves
     │
     ▼
Phase 17+:                Real-time fleet streaming (Spark Streaming)
     • 100+ spacecraft, sub-100ms anomaly detection
```

---

## 5. Minimal Spark Setup for Phase 14

If Monte Carlo is approved for Phase 14:

| Component | Specification |
|-----------|---------------|
| **Cluster** | 50-100 worker nodes (r6g.2xlarge: 8 vCPU, 64 GB) |
| **Runtime** | Databricks / EMR / Kubernetes (Spark Operator) |
| **Schedule** | Weekly batch (or on-demand for design reviews) |
| **Input** | JPL covariance matrix + nominal trajectory |
| **Output** | `mc_trajectory_envelopes` table (small, for dashboard) + full ensemble Parquet (S3) |
| **Cost** | ~$500-2,000/run (vs. $200/mo for current pipeline) |

**Key principle**: Spark runs **offline/batch**. The real-time pipeline (Phases 1-13) stays Python + TimescaleDB.

---

## 6. Summary for Stakeholders

| Question | Answer |
|----------|--------|
| **Is Spark needed today?** | No. Current load: < 1 GB/day. TimescaleDB + Python scales to 500 GB/day. |
| **When is Spark justified?** | Monte Carlo ensembles (10K+ runs), multi-mission fleet, or petabyte ML. |
| **What's the simplest Spark entry point?** | Phase 14: Weekly Monte Carlo trajectory batch job. |
| **Does Spark replace the current pipeline?** | No. It augments it with a separate batch analytics layer. |
| **What if we never need Monte Carlo?** | Never install Spark. The deterministic pipeline is complete without it. |

---

## 7. Glossary

| Term | Definition |
|------|------------|
| **Monte Carlo** | Running a simulation thousands of times with random inputs to understand uncertainty |
| **Covariance matrix** | Mathematical description of how uncertain each input is, and how they correlate |
| **Percentile envelope** | The "tube" showing 5th/50th/95th percentile bounds across all Monte Carlo runs |
| **3-sigma** | 99.7% confidence interval (3 standard deviations from mean) |
| **Embarrassingly parallel** | Work that splits into independent pieces with no communication needed |
| **CFD** | Computational Fluid Dynamics — 3D simulation of fluid flow and heat transfer |
| **FEM** | Finite Element Method — 3D simulation of structural stress, thermal conduction |
| **Domain decomposition** | Splitting a 3D mesh across multiple CPUs for parallel solving |
| **MPI** | Message Passing Interface — standard for inter-process communication in HPC |
| **Structured Streaming** | Spark's streaming engine with exactly-once guarantees and event-time processing |
| **Broadcast variable** | Read-only data sent once to all workers (e.g., ML model weights) |

---

## 8. Next Steps

1. **Confirm Phase 14 scope** with stakeholders: Is Monte Carlo uncertainty quantification a funded requirement?
2. **If yes**: Prototype `spark_jobs/monte_carlo_trajectory.py` with 100 runs locally (no cluster needed for dev)
3. **If no**: Document "Spark not required" in architecture decision record (ADR) and move on.
4. **Revisit** at each phase gate — requirements evolve.

---

*Document created to satisfy "Spark as requirement" while being honest about where it adds value vs. complexity.*