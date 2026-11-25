# No Spark until a measured limit needs it

> **Status:** accepted. The full analysis, written by Eveliina Vesala, is in
> [`docs/archive/SPARK_SCALE_REQUIREMENTS.md`](../archive/SPARK_SCALE_REQUIREMENTS.md).

## Context

A digital twin computes behaviour from planned inputs: the published trajectory, the
planned attitude timeline, assumed material properties and modelled environments. Every
input is uncertain, so a single deterministic run gives a falsely precise answer. Monte
Carlo sampling (running the models many times with varied inputs) turns the output into
ranges and limit-violation probabilities, and gives anomaly detection a baseline: "outside
the plausible envelope". Running many samples raises the question of whether Apache Spark
is needed.

## Decision

- Monte Carlo uncertainty quantification is the most valuable **future** extension. It is
  not built.
- Spark is **not** adopted. A Monte Carlo layer would start on one machine: models written
  as pure functions of their inputs, efficient sampling and surrogate models.
- A cluster (Spark or a plain job scheduler) is considered only once a measured limit is
  hit: runtime, memory or result volume versus the turnaround that is needed. A requirement
  alone does not justify it.

| Need | Try first | Consider Spark when |
|------|-----------|---------------------|
| Monte Carlo over the models | Multi-core single machine, sampling, surrogates | Measured runtime, memory or result volume exceeds the turnaround |
| Analytics across missions | Polars / DuckDB on Parquet | Data or joins no longer fit one machine |
| 3D physics solves | HPC solvers (MPI) | Never for the solve itself |
| Streaming many spacecraft | Kafka consumers / Flink | Latency target is seconds and the logic is complex |

## Consequences

- The stack stays small: one server, PostgreSQL and a 1 Hz simulator.
- `pipelines` has no PySpark dependency. If one is ever added, use Spark 4.x on Java 21
  (see `CLAUDE.md`).
- The models are already deterministic functions of their inputs and the timestamp, which
  keeps a later sampling layer possible.
