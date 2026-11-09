import pytest


def test_ingest_command_runs_module_with_pipelines_venv(real_data_sources):
    assert (
        real_data_sources.ingest_command("jpl_orion")
        == "/opt/pipelines/.venv/bin/python -m pipelines.ingest.jpl_orion"
    )


def test_ingest_command_rejects_unknown_source(real_data_sources):
    with pytest.raises(ValueError, match="unknown ingest source"):
        real_data_sources.ingest_command("jpl_orion; rm -rf /")
