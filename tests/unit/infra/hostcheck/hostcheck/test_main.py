import pytest


@pytest.fixture
def healthy(monkeypatch, hostcheck, docker, http, disk, make_container):
    """Everything OK; the ping URL comes from .env like on the server."""
    docker.containers = [make_container("backend", health="healthy")]
    monkeypatch.setenv("HOSTCHECK_SITE_URL", "https://demo.example/_stcore/health")
    (hostcheck.REPO / ".env").write_text("HOSTCHECK_PING_URL=https://hc-ping.com/abc\n")
    return http


def test_main_sends_a_success_ping_when_all_is_well(hostcheck, healthy):
    assert hostcheck.main() == 0
    assert healthy.pings == [("https://hc-ping.com/abc", "ok: disk 40%, all containers healthy, site up")]


def test_main_sends_every_problem_to_the_fail_url(hostcheck, healthy, docker, disk, make_container):
    disk.percent = 90
    docker.containers = [make_container("backend", health="unhealthy")]
    assert hostcheck.main() == 1
    assert healthy.pings == [("https://hc-ping.com/abc/fail", "disk 90% used (limit 85%)\nbackend is unhealthy")]


def test_main_reports_nothing_without_a_ping_url(hostcheck, healthy):
    (hostcheck.REPO / ".env").write_text("PUBLIC_HOSTNAME=demo.example\n")
    assert hostcheck.main() == 2
    assert healthy.pings == []


def test_main_survives_an_unreachable_ping_url(hostcheck, healthy):
    healthy.ping_error = healthy.url_error
    assert hostcheck.main() == 0  # logged; healthchecks.io alerts on the missing ping itself
