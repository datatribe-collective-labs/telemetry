# Monitoring with Grafana and healthchecks.io

> **Status:** accepted and running since 2026-11-24 (#46; #106, #108, #110, #112).
> Operating it: [`guides/MONITORING.md`](../guides/MONITORING.md).

## Context

The public demo runs unattended on one server. When it breaks, someone should hear about
it with a first thing to check. The project ends in mid-December 2026, so the setup has to
be small. Two kinds of failure matter:

- **The data stops** while the site still loads: the simulator, consumer or an ingest job
  fails, or the database fills up.
- **The server or a container fails**: the disk is full, a container is unhealthy or
  restarting, or the public site is down. Grafana cannot see these from the database, and
  it cannot report its own failure.

## Decision

Two independent checks, each emailing when something is wrong:

1. **Grafana** (self-hosted container, `docker-compose.grafana.yml`; UpCloud has no
   managed Grafana). It reads the database with a read-only role. Its "Telemetry ops"
   dashboard and four email alerts (pipeline stopped, missing ticks, real-data refresh
   failed, database almost full) are provisioned from `infra/grafana/`. Each alert runs a
   dashboard tile's SQL unchanged, and a unit test enforces that. Grafana is reachable only
   over an SSH tunnel.
2. **A host check** (`infra/hostcheck/hostcheck.py`, Python standard library only, run by
   the deploy user's crontab every 5 minutes). It checks disk, container state, health,
   restarts and the public HTTPS site, then pings a **healthchecks.io** check. A failure
   ping carries the reasons. If no ping arrives, healthchecks.io emails anyway, which also
   covers the server itself being down.

Alerts are sent from a dedicated Gmail account over SMTP (port 587; UpCloud blocks 25).

## Rejected

- **Prometheus + cAdvisor:** cAdvisor does not see Docker health checks, and it would
  have added two services and an alerting path to learn for a few weeks of use.
- **Only Grafana:** a hung backend, a full disk or a dead server would raise no alert.

## Consequences

- Failure drills (stopping the consumer, pausing cron) were run on the live server and
  are documented in [`guides/MONITORING.md`](../guides/MONITORING.md#drills).
- Before a planned restart, silence the Grafana alerts first ([Planned restarts](../guides/MONITORING.md#planned-restarts)).
- At project end, delete the healthchecks.io check and the alert Gmail account along with
  the server.
