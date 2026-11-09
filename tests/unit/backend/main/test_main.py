from unittest.mock import MagicMock

import pytest
from backend import main as backend_main


@pytest.fixture
def uvicorn_run(monkeypatch):
    run = MagicMock()
    monkeypatch.setattr(backend_main.uvicorn, "run", run)
    return run


def test_main_runs_without_reload_by_default(monkeypatch, uvicorn_run):
    monkeypatch.delenv("BACKEND_RELOAD", raising=False)
    backend_main.main()
    uvicorn_run.assert_called_once()
    assert uvicorn_run.call_args.args == ("backend.api:app",)
    assert uvicorn_run.call_args.kwargs["reload"] is False
    assert uvicorn_run.call_args.kwargs["port"] == 8000


def test_main_reloads_when_backend_reload_is_1(monkeypatch, uvicorn_run):
    monkeypatch.setenv("BACKEND_RELOAD", "1")
    backend_main.main()
    assert uvicorn_run.call_args.kwargs["reload"] is True


def test_main_ignores_other_backend_reload_values(monkeypatch, uvicorn_run):
    monkeypatch.setenv("BACKEND_RELOAD", "true")
    backend_main.main()
    assert uvicorn_run.call_args.kwargs["reload"] is False
