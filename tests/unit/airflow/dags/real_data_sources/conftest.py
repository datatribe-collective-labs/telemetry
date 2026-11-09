import importlib.util
from pathlib import Path

import pytest

DAGS_DIR = Path(__file__).parents[5] / "airflow" / "dags"


@pytest.fixture
def real_data_sources():
    """airflow/dags/real_data_sources.py, loaded by path (airflow/dags is not a package)."""
    spec = importlib.util.spec_from_file_location("real_data_sources", DAGS_DIR / "real_data_sources.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module
