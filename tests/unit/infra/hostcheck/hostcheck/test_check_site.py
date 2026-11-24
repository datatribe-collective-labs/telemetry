def test_check_site_passes_when_the_health_page_says_ok(hostcheck, http, monkeypatch):
    monkeypatch.setenv("HOSTCHECK_SITE_URL", "https://demo.example/_stcore/health")
    assert hostcheck.check_site() == []


def test_check_site_uses_the_public_hostname_from_env(hostcheck, http, tmp_path, monkeypatch):
    (tmp_path / "repo/.env").write_text("PUBLIC_HOSTNAME=demo.example\n")
    seen = []
    real = hostcheck.urllib.request.urlopen
    monkeypatch.setattr(hostcheck.urllib.request, "urlopen", lambda url, timeout=None: seen.append(url) or real(url))
    assert hostcheck.check_site() == []
    assert seen == ["https://demo.example/_stcore/health"]


def test_check_site_fails_for_another_answer(hostcheck, http, monkeypatch):
    monkeypatch.setenv("HOSTCHECK_SITE_URL", "https://demo.example/_stcore/health")
    http.site_body = "<html>502 Bad Gateway</html>"
    (problem,) = hostcheck.check_site()
    assert problem.startswith("public site answered")


def test_check_site_fails_when_unreachable(hostcheck, http, monkeypatch):
    monkeypatch.setenv("HOSTCHECK_SITE_URL", "https://demo.example/_stcore/health")
    http.site_error = http.url_error
    (problem,) = hostcheck.check_site()
    assert problem.startswith("public site check failed: URLError")


def test_check_site_fails_without_a_public_hostname(hostcheck, http):
    assert hostcheck.check_site() == ["PUBLIC_HOSTNAME not set in .env"]
