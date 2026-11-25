# UpCloud Managed PostgreSQL on the public server

> **Status:** accepted 2026-11-16 and in production since then (#46, PRs #69 and #70).
> How to set it up: [`guides/UPCLOUD_DEPLOYMENT.md`](../guides/UPCLOUD_DEPLOYMENT.md).

## Context

The first public deployment (2026-11-16) ran the database as the `timescaledb` container
on the same server as everything else. One disk held the data, the app and the Docker
images, and nothing backed it up. A server failure would lose the database along with the
app.

## Decision

On the public server, use **UpCloud Managed PostgreSQL** (PostgreSQL 16 with the
TimescaleDB extension) instead of the container:

- the smallest plan (1 core, 2 GiB memory, 10 GiB storage): the data is tens of MB,
- no public connection: the server reaches it over UpCloud's private network,
- TLS required (`POSTGRES_SSLMODE=require`),
- termination protection on.

It is opt-in through a third compose file, `docker-compose.managed-db.yml`, enabled with
`COMPOSE_FILE` in the server's `.env`. It points every service at `POSTGRES_HOST` and
`POSTGRES_PORT` and leaves the `timescaledb` container out. Laptops keep the container.

## Consequences

- UpCloud backs the database up (included in the price) and maintains it in a weekly
  window (Sunday 05:00 UTC). The Grafana alerts' pending periods ride out that window.
- The app, the `airflow` database and the read-only Grafana role (`grafana_ro`) all live
  on the managed instance.
- It is an extra monthly cost. At project end, termination protection must be turned off
  before the database can be deleted (runbook, "Shutting down").
- No data was copied at the switch: the real data was ingested again with the backfill
  DAG, and the simulator regenerates the synthetic data.
