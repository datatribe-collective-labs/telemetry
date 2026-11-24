"""Fixtures for infra/hostcheck/hostcheck.py: a freshly loaded module per test, with every path
pointing into tmp_path, and fakes for docker, the disk and HTTP."""

import importlib.util
import json
import subprocess
import urllib.error
from pathlib import Path
from types import SimpleNamespace

import pytest

SCRIPT = Path(__file__).resolve().parents[5] / "infra/hostcheck/hostcheck.py"


@pytest.fixture
def hostcheck(monkeypatch, tmp_path):
    """The script as a module; HOSTCHECK_REPO/STATE in tmp_path; no ping URL or site URL set."""
    for var in ("HOSTCHECK_PING_URL", "HOSTCHECK_SITE_URL", "HOSTCHECK_PROJECT", "HOSTCHECK_DISK_LIMIT",
                "HOSTCHECK_ONE_SHOT"):
        monkeypatch.delenv(var, raising=False)
    (tmp_path / "repo").mkdir()
    monkeypatch.setenv("HOSTCHECK_REPO", str(tmp_path / "repo"))
    monkeypatch.setenv("HOSTCHECK_STATE", str(tmp_path / "state" / "restarts.json"))
    spec = importlib.util.spec_from_file_location("hostcheck", SCRIPT)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    monkeypatch.setattr(module, "log", lambda message: None)
    return module


def container(service, status="running", health=None, exit_code=0, restarts=0, oom=False, cid=None):
    """One `docker inspect` entry, with only the fields the script reads."""
    state = {"Status": status, "ExitCode": exit_code, "OOMKilled": oom}
    if health:
        state["Health"] = {"Status": health}
    return {"Id": cid or f"id-{service}", "Name": f"/telemetry-{service}-1", "RestartCount": restarts,
            "State": state, "Config": {"Labels": {"com.docker.compose.service": service}}}


@pytest.fixture
def docker(monkeypatch, hostcheck):
    """Fake `docker ps` / `docker inspect`: set `.containers` (a list) or `.error` (an exception)."""
    fake = SimpleNamespace(containers=[], error=None, calls=[])

    def run(args, **kwargs):
        fake.calls.append(args)
        if fake.error:
            raise fake.error
        if args[:2] == ["docker", "ps"]:
            out = "\n".join(c["Id"] for c in fake.containers)
        else:
            out = json.dumps([c for c in fake.containers if c["Id"] in args[2:]])
        return subprocess.CompletedProcess(args, 0, stdout=out, stderr="")

    monkeypatch.setattr(hostcheck.subprocess, "run", run)
    return fake


@pytest.fixture
def http(monkeypatch, hostcheck):
    """Fake urlopen: GETs answer `.site_body` (or raise `.site_error`); POSTs are recorded in `.pings`."""
    fake = SimpleNamespace(site_body="ok", site_error=None, ping_error=None, pings=[])

    class Response:
        def __init__(self, body):
            self.body = body.encode()

        def read(self, n=-1):
            return self.body

        def close(self):
            pass

        def __enter__(self):
            return self

        def __exit__(self, *exc):
            return False

    def urlopen(request, timeout=None):
        if isinstance(request, str):
            if fake.site_error:
                raise fake.site_error
            return Response(fake.site_body)
        if fake.ping_error:
            raise fake.ping_error
        fake.pings.append((request.full_url, request.data.decode()))
        return Response("OK")

    monkeypatch.setattr(hostcheck.urllib.request, "urlopen", urlopen)
    fake.url_error = urllib.error.URLError("no route")
    return fake


@pytest.fixture
def disk(monkeypatch, hostcheck):
    """Fake disk usage of /: set `.percent`."""
    fake = SimpleNamespace(percent=40)
    monkeypatch.setattr(hostcheck.shutil, "disk_usage",
                        lambda path: SimpleNamespace(total=100, used=fake.percent, free=100 - fake.percent))
    return fake


@pytest.fixture
def make_container():
    return container
