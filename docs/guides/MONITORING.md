# Monitoring the public demo

How the server tells you when the demo breaks, and what to do then. Two independent checks
email the alert inbox:

- **Grafana** reads the database: is the data flowing, is the real data fresh, is the
  database filling up? Ops dashboard and four email alerts, provisioned from `infra/grafana/`
  (`docker-compose.grafana.yml`).
- **The host check** (`infra/hostcheck/hostcheck.py`) looks at the server itself: disk,
  containers and the public site. It pings healthchecks.io, which also emails when the
  server goes silent.

Why this setup: [`decisions/MONITORING.md`](../decisions/MONITORING.md). Server set-up and
everyday operations: [`UPCLOUD_DEPLOYMENT.md`](UPCLOUD_DEPLOYMENT.md). All commands run on
the server from `~/telemetry` as `deploy`.

## Ops dashboard (Grafana)

One read-only dashboard, "Telemetry ops" (`infra/grafana/`). The status row answers "is
everything OK?": **Pipeline** (all 8 tick tables written in the last 2-5 min, about 60
writes a minute), **Real data** (daily sources under 26/36 h, backfill tables not empty),
**Airflow** (the last `real_data_refresh` succeeded under 26/36 h ago), **Replay position**
and **Database use** (of the 10 GiB plan). Each tile's description says what to check
first. Below: **Mission checks** on the stored synthetic data (red = broken data; orange =
the model output changed, so a physics model PR updates the expected no-link count and
final dose there), the real-data tables, writes per minute and the latest Airflow runs;
raw counts and sizes under Details.
Private like the Airflow UI; about 220 MB of memory. Set up once, on the server:

```bash
cd ~/telemetry
cat >> .env <<EOF

# Grafana ops dashboard: docker-compose.grafana.yml
GRAFANA_ADMIN_PASSWORD=$(openssl rand -hex 32)
GRAFANA_DB_USER=grafana_ro
GRAFANA_DB_PASSWORD=$(openssl rand -hex 32)
EOF

# A read-only database user for it (Grafana's query editor runs any SQL its user may)
set -a; . ./.env; set +a
PG() { docker run --rm -i -e PGPASSWORD="$POSTGRES_PASSWORD" postgres:16-alpine psql \
  "host=$POSTGRES_HOST port=$POSTGRES_PORT user=$POSTGRES_USER dbname=$1 sslmode=require" -v ON_ERROR_STOP=1 "${@:2}"; }
PG defaultdb -v pw="$GRAFANA_DB_PASSWORD" <<'SQL'
SELECT format('CREATE ROLE grafana_ro LOGIN PASSWORD %L', :'pw') \gexec
GRANT CONNECT ON DATABASE telemetry, airflow TO grafana_ro;
SQL
for db in telemetry airflow; do PG $db <<'SQL'
GRANT USAGE ON SCHEMA public TO grafana_ro;
GRANT SELECT ON ALL TABLES IN SCHEMA public TO grafana_ro;
ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT SELECT ON TABLES TO grafana_ro;
SQL
done
```

Then add `:docker-compose.grafana.yml` to the end of `COMPOSE_FILE` in `.env`, run
`docker compose up -d --wait`, and copy `GRAFANA_ADMIN_PASSWORD` into the password
manager. `ALTER DEFAULT PRIVILEGES` covers tables created later (by `upadmin`).

## Email alerts

Grafana emails when the demo breaks (`infra/grafana/provisioning/alerting/`, #108). Each rule
runs a status tile's query, so an email and the dashboard always agree:

| Alert | Fires when | After | First check |
|---|---|---|---|
| Pipeline stopped | Pipeline tile = Stopped | 5 min | `docker compose ps`, then the `physics_models` and `physics_models_consumer` logs |
| Missing ticks | Pipeline tile = Slow | 10 min | the consumer log for rejected ticks; "Synthetic writes per minute" |
| Real-data refresh failed | Airflow tile = Failed | 5 min | the failed task's log in the Airflow UI |
| Database almost full | Database use over 80% | 30 min | "Rows per table" and "Database size" under Details |

A query error or no data fires the rule too (the database is unreachable); the waiting
period rides out the database's Sunday maintenance and a deploy restart. A reminder
follows every 4 h while a problem lasts, and a "resolved" email when it's fixed. Server
down, disk and container health are not covered here.

The sender is a dedicated Gmail account (not a personal one: an app password opens the
whole mailbox), over port 587 because UpCloud blocks 25. Set up once:

1. Create the Gmail account (recovery email: your own), turn on 2-Step Verification, then
   create an app password at <https://myaccount.google.com/apppasswords> (Security ->
   2-Step Verification -> App passwords). Save it in the password manager.
2. Add three lines at the end of `.env`, with `nano` (no quotes, brackets or spaces; the app
   password is 16 letters, without the spaces Google shows):
   ```
   GRAFANA_SMTP_USER=<the sending Gmail address>
   GRAFANA_SMTP_PASSWORD=<the app password>
   GRAFANA_ALERT_EMAIL=<who gets the alerts>
   ```
3. `docker compose up -d --force-recreate grafana`, then send a test email: Grafana ->
   Alerting -> Contact points -> "Alert email" -> Test.

Changing the Gmail account's password revokes the app password: create a new one and
update `.env`. Before a planned restart of the simulator or the database, a silence
(Alerting -> Silences) keeps the alerts quiet.

## Host check (healthchecks.io)

Grafana only sees the database, so it can't report the server being down, a full disk or
a hung backend (the site still answers, the data still flows). `infra/hostcheck/hostcheck.py`
(#110) covers those: cron runs it every 5 minutes, and it pings
[healthchecks.io](https://healthchecks.io), which emails when a ping says something is
wrong, or when no ping arrives at all (server, network or cron down).

| Problem line | Means | First check |
|---|---|---|
| `disk N% used` | `/` over 85% full | `docker system df`, then prune old images and the build cache |
| `<service> is exited` | a long-running service stopped | `docker compose ps`, `docker compose logs --tail 50 <service>` |
| `<service> is unhealthy` | it runs but fails its healthcheck (a hung backend, say); Docker doesn't restart it | its log, then `docker compose restart <service>` |
| `<service> restarted Nx` | crashed and was restarted since the last check | its log; repeated: a crash loop |
| `<service> was killed: out of memory` | hit its memory limit | `docker stats`; the limits are in `docker-compose.prod.yml` |
| `migrate exited with code N` | a one-shot job failed (after a deploy) | `docker compose logs migrate` |
| `public site ...` | Caddy, the certificate or the dashboard doesn't answer | `docker compose logs caddy dashboard` |
| `docker check failed` | Docker itself doesn't answer | `sudo systemctl status docker` |
| no ping (healthchecks.io says "down") | the server, its network or cron is down | the UpCloud console |

It only checks the `telemetry` compose project, never prints `.env` values and writes one
line per run to the system log (`journalctl -t hostcheck`). A check from outside (a
firewall mistake that blocks visitors while the server works) is not covered.

Set up once:

1. On healthchecks.io (sign up with the alert Gmail account): add a check with
   **Period 5 minutes** and **Grace 10 minutes**, and copy its ping URL to the password
   manager.
2. Add it at the end of `.env` with `nano`: `HOSTCHECK_PING_URL=https://hc-ping.com/<uuid>`
3. Run it once by hand; it prints `ok: ...` or the problems, and the check turns green:
   `python3 ~/telemetry/infra/hostcheck/hostcheck.py`
4. Add the cron line (`crontab -e`):
   ```
   */5 * * * * /usr/bin/python3 $HOME/telemetry/infra/hostcheck/hostcheck.py >/dev/null 2>&1
   ```

A deploy needs nothing extra: `git pull` updates the script, and recreated containers
start a new restart count. To pause it, comment out the cron line, or pause the check on
healthchecks.io (it then also stops alerting on missing pings).

## When an alert arrives

All alerts go to the alert inbox (the dedicated Gmail account). Two senders:

| Email | From | What to do |
|---|---|---|
| `[FIRING:n] Telemetry (...)` | Grafana ("Telemetry ops") | The data path: find the alert in [Email alerts](#email-alerts). Each email has its first check and links to the dashboard panel (open the Grafana SSH tunnel first) |
| `[RESOLVED] Telemetry` | Grafana | The problem is gone; nothing to do |
| `DOWN \| <check name>` | healthchecks.io | The server. "received a failure signal": the email's **Last Ping Body** lists the problem lines (e.g. `physics_models_consumer is exited`), see [Host check](#host-check-healthchecksio). "success signal did not arrive on time, grace time passed": no ping at all for 15 minutes (the Last Ping Body is then an old `ok: ...`), so the server, its network or cron is down; look in the UpCloud console |
| `UP \| <check name>` | healthchecks.io | Recovered |

Then, in order: `docker compose ps` (what is down?), the service's log, the Grafana status
row (what does the data say?). Bring one stopped service back with
`docker compose up -d --no-deps <service>`, or restart a running one with
`docker compose restart <service>`. **Not `docker compose start <service>`**: it also
starts the one-shot jobs the service depends on (`migrate`) from their old containers,
which can be older than the database ([drill 1](#drills)). A reminder follows every 4 h while
a Grafana alert lasts; healthchecks.io emails once per change.

**"Values" in a Grafana email** are the rule's two steps. **A** is the query's result, the
same number as the dashboard tile: the status code for Pipeline and Airflow (0 = OK,
1 = Slow/Late, 2 = Stopped/Failed), the % used for "Database almost full". **C** is the
condition: 1 = firing, 0 = not. So `A=2 C=1` on "Pipeline stopped" means Stopped and
firing, and `A=0 C=0` in a resolved email means back to OK. "Missing ticks" fires on A = 1
only: when the pipeline stops completely (A = 2), "Pipeline stopped" takes over.

The synthetic data survives a consumer outage of up to an hour: Redpanda keeps the
simulator's messages for 1 h, and the restarted consumer writes them all.

## Planned restarts

A deploy that restarts `physics_models` or `physics_models_consumer`, or the database's
maintenance, pauses the synthetic data. Grafana waits 5-10 minutes before alerting, so a
quick restart sends nothing. For anything longer, silence it first: Grafana -> Alerting ->
Silences -> New silence, label `grafana_folder` = `Telemetry`, duration 1h (end it early
when done). If a host check run lands in the middle of a rebuild, it reports the container
being recreated as stopped; the next run, 5 minutes later, sends "up" again. To avoid even
that, pause the check on healthchecks.io during the deploy and resume it after.

After a deploy, drop superseded rollback image tags and `docker builder prune -f`, so the
disk doesn't refill (it reached 83% before the first cleanup). A deploy that rebuilds the
backend image should also recreate `migrate` (`docker compose up -d --no-deps migrate`;
at the latest revision it does nothing and exits 0), so the job isn't left on an old image.

## Drills

Run on the live server, 2026-11-24 (#112):

| Drill | What happened | Result |
|---|---|---|
| 1. `physics_models_consumer` stopped 10:53-11:07 UTC (about 13.5 min) | 10:55 host check `/fail` ("physics_models_consumer is exited"), healthchecks.io `DOWN` email at once; 10:58 Grafana "Pipeline stopped" pending, 11:04 firing, email; consumer back 11:07; 11:07 Grafana inactive, `[RESOLVED]`; 11:10 host check ok, `UP` email | All emails as designed. Mission checks after: 12,834 ticks, 0 gaps (the consumer caught up from Redpanda). Found: `docker compose start` also ran a `migrate` container from 2026-11-16 that failed (exit 255, the host check reported it); fixed by recreating it, and the runbook now says `up -d --no-deps` |
| 2. Host check cron paused 11:10-11:28 UTC (stand-in for "server down") | Last ping 11:10:01; 11:25:02 healthchecks.io `DOWN` ("success signal did not arrive on time, grace time passed"), exactly period + grace later; cron line back 11:28; 11:30 ping, `UP` email | As designed: a silent server is reported within 15 minutes, worded differently from a reported problem |

Not drilled live (tested locally, would need real damage here): refresh failed, database
almost full, disk, out of memory, unhealthy container, public site down.
