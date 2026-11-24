#!/usr/bin/env python3
"""Is the server itself OK? (#46, step 3) Run by the deploy user's crontab every 5 minutes:

    */5 * * * * /usr/bin/python3 $HOME/telemetry/infra/hostcheck/hostcheck.py

Checks what Grafana can't see from the database: disk, container health, crashes and the
public site. Pings an outside dead man's switch (healthchecks.io, HOSTCHECK_PING_URL in .env):
a success ping when all is well, /fail with one line per problem otherwise. No ping at all
(server, network or cron down) alerts there after the check's grace time. Each run logs one
line to the system log: `journalctl -t hostcheck`.

Standard library only. .env is read for two keys and never executed. A check that can't run
(Docker not answering, say) is reported as a problem, never as OK. The HOSTCHECK_* variables
below override the defaults, e.g. for tests.
"""

import json
import os
import shutil
import subprocess
import sys
import urllib.error
import urllib.request
from pathlib import Path

HOME = Path.home()
REPO = Path(os.environ.get("HOSTCHECK_REPO", HOME / "telemetry"))
PROJECT = os.environ.get("HOSTCHECK_PROJECT", "telemetry")  # compose project (not throwaway stacks)
DISK_LIMIT = int(os.environ.get("HOSTCHECK_DISK_LIMIT", "85"))  # % of / used
ONE_SHOT = set(os.environ.get("HOSTCHECK_ONE_SHOT", "migrate airflow-init").split())  # run once, exit
STATE = Path(os.environ.get("HOSTCHECK_STATE", HOME / ".local/state/hostcheck/restarts.json"))
TIMEOUT = 10  # seconds, for every outside call


def log(message):
    """One line in the system log (`journalctl -t hostcheck`); a no-op where there's no syslog."""
    try:
        import syslog
    except ImportError:  # Windows, where the unit tests also run
        return
    syslog.openlog("hostcheck")
    syslog.syslog(message)


def env_value(key):
    """KEY's value in the repo's .env (plain KEY=value lines only), or ''."""
    try:
        for line in (REPO / ".env").read_text(encoding="utf-8").splitlines():
            if line.startswith(key + "="):
                return line[len(key) + 1:].strip()
    except OSError:
        pass
    return ""


def check_disk():
    usage = shutil.disk_usage("/")
    used = round(100 * usage.used / usage.total)
    problems = [f"disk {used}% used (limit {DISK_LIMIT}%)"] if used > DISK_LIMIT else []
    return used, problems


def check_containers():
    """Long-running services running and not unhealthy; one-shot jobs exited 0; no new restarts."""
    try:
        ids = subprocess.run(
            ["docker", "ps", "-aq", "--filter", f"label=com.docker.compose.project={PROJECT}"],
            capture_output=True, text=True, timeout=TIMEOUT, check=True).stdout.split()
        if not ids:
            return [f"no containers found for compose project '{PROJECT}'"]
        containers = json.loads(subprocess.run(["docker", "inspect", *ids], capture_output=True, text=True,
                                               timeout=TIMEOUT, check=True).stdout)
    except (OSError, subprocess.SubprocessError, json.JSONDecodeError) as e:
        return [f"docker check failed: {type(e).__name__}: {str(e)[:120]}"]

    try:
        before = json.loads(STATE.read_text())
    except (OSError, json.JSONDecodeError):
        before = {}
    after, problems = {}, []
    for c in containers:
        name = c["Config"]["Labels"].get("com.docker.compose.service", c["Name"].lstrip("/"))
        state = c["State"]
        if name in ONE_SHOT:
            if state["Status"] == "exited" and state["ExitCode"] != 0:
                problems.append(f"{name} exited with code {state['ExitCode']}")
            continue
        if state["Status"] != "running":
            problems.append(f"{name} is {state['Status']}")
        elif (state.get("Health") or {}).get("Status") == "unhealthy":  # a stopped one keeps its last status
            problems.append(f"{name} is unhealthy")
        if state.get("OOMKilled"):
            problems.append(f"{name} was killed: out of memory")
        restarts = c["RestartCount"]
        # Keyed by container id: a deploy recreates containers (new ids), so their counts start over.
        if restarts > before.get(c["Id"], restarts):
            problems.append(f"{name} restarted {restarts - before[c['Id']]}x since the last check")
        after[c["Id"]] = restarts
    STATE.parent.mkdir(parents=True, exist_ok=True)
    STATE.write_text(json.dumps(after))
    return problems


def check_site():
    """Caddy, the certificate and the dashboard answer: Streamlit's health page says ok."""
    url = os.environ.get("HOSTCHECK_SITE_URL")
    if not url:
        host = env_value("PUBLIC_HOSTNAME")
        if not host:
            return ["PUBLIC_HOSTNAME not set in .env"]
        url = f"https://{host}/_stcore/health"
    try:
        with urllib.request.urlopen(url, timeout=TIMEOUT) as r:
            body = r.read(200).decode(errors="replace").strip()
    except (OSError, urllib.error.URLError) as e:
        return [f"public site check failed: {type(e).__name__}: {str(e)[:120]}"]
    return [] if body == "ok" else [f"public site answered {body[:60]!r}, not 'ok'"]


def ping(url, report):
    for _ in range(3):
        try:
            urllib.request.urlopen(urllib.request.Request(url, data=report.encode()), timeout=TIMEOUT).close()
            return True
        except (OSError, urllib.error.URLError):
            continue
    return False


def main():
    used, problems = check_disk()
    problems += check_containers()
    problems += check_site()
    report = "\n".join(problems) if problems else f"ok: disk {used}%, all containers healthy, site up"

    log(("FAIL: " + "; ".join(problems)) if problems else report)
    print(report)

    ping_url = os.environ.get("HOSTCHECK_PING_URL") or env_value("HOSTCHECK_PING_URL")
    if not ping_url:
        log("HOSTCHECK_PING_URL not set in .env: nothing reported")
        print("HOSTCHECK_PING_URL not set in .env", file=sys.stderr)
        return 2
    if not ping(ping_url.rstrip("/") + ("/fail" if problems else ""), report):
        log("could not reach the ping URL")
    return 1 if problems else 0


if __name__ == "__main__":
    sys.exit(main())
