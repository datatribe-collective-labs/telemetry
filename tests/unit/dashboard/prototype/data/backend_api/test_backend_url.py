from dashboard.src.prototype.data.backend_api import (
    DEFAULT_BACKEND_URL,
    BackendAPI,
    backend_url,
)


def test_backend_url_defaults_to_localhost(monkeypatch):
    monkeypatch.delenv("BACKEND_URL", raising=False)
    assert backend_url() == DEFAULT_BACKEND_URL == "http://localhost:8000"


def test_backend_url_reads_env_var(monkeypatch):
    monkeypatch.setenv("BACKEND_URL", "http://backend:8000")
    assert backend_url() == "http://backend:8000"


def test_backend_url_ignores_blank_env_var(monkeypatch):
    monkeypatch.setenv("BACKEND_URL", "  ")
    assert backend_url() == DEFAULT_BACKEND_URL


def test_backend_url_used_by_client_without_explicit_url(monkeypatch):
    monkeypatch.setenv("BACKEND_URL", "http://backend:8000/")
    api = BackendAPI()
    try:
        assert api.base_url == "http://backend:8000"
    finally:
        api.close()


def test_backend_url_overridden_by_explicit_url(monkeypatch):
    monkeypatch.setenv("BACKEND_URL", "http://backend:8000")
    api = BackendAPI("http://example.test:9000")
    try:
        assert api.base_url == "http://example.test:9000"
    finally:
        api.close()
