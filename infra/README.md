# infra

Configuration for running the demo on a public server: HTTPS and monitoring. None of it is
needed on a laptop. Server runbook: [`docs/guides/UPCLOUD_DEPLOYMENT.md`](../docs/guides/UPCLOUD_DEPLOYMENT.md);
monitoring: [`docs/guides/MONITORING.md`](../docs/guides/MONITORING.md).

## `caddy/`

`Caddyfile`: the only public entry point, used by `docker-compose.prod.yml`. Caddy
gets and renews the HTTPS certificate for `PUBLIC_HOSTNAME`, redirects HTTP to HTTPS and
proxies to the dashboard (its WebSocket included). The certificates live in the
`caddy_data` volume: never `docker compose down -v` on the server.

## `grafana/`

Provisioning for the Grafana service in `docker-compose.grafana.yml` (opt-in compose file,
`127.0.0.1:3000`, read-only database user):

| Path | Holds |
|------|-------|
| `provisioning/datasources/postgres.yml` | The `telemetry` and `airflow` databases |
| `provisioning/dashboards/dashboards.yml` + `dashboards/telemetry-ops.json` | The "Telemetry ops" dashboard: status row, mission data checks, real-data freshness, Airflow runs |
| `provisioning/alerting/telemetry-alerts.yml` | Four email alerts: pipeline stopped, missing ticks, real-data refresh failed, database almost full |

Each alert runs the SQL of a dashboard tile unchanged, so an email and the dashboard always
agree; `tests/unit/infra/grafana/` enforces it. Change the dashboard by editing the JSON:
the UI cannot save changes to it (`allowUiUpdates: false`).

## `hostcheck/`

`hostcheck.py`: checks what Grafana can't see from the database, from the deploy user's
crontab every 5 minutes. It looks at disk use, the compose project's containers (running,
healthy, restarts, out-of-memory kills, failed one-shot jobs) and the public site, then pings
healthchecks.io (`HOSTCHECK_PING_URL`), with the problems listed when there are any. It uses
the Python standard library only, and reads two keys from `.env` without executing it.

```bash
python3 infra/hostcheck/hostcheck.py        # prints "ok: ..." or the problems
uv run pytest tests/unit/infra/hostcheck    # unit tests
```
