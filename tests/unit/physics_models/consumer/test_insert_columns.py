import importlib.util
from pathlib import Path
from unittest.mock import MagicMock

import pytest
from contracts import (
    SyntheticCommsOutput,
    SyntheticRadiationOutput,
    SyntheticTelemetryPacket,
)

CONSUMER_PATH = Path(__file__).parents[4] / "packages" / "physics_models" / "consumer.py"


@pytest.fixture
def consumer_class(monkeypatch):
    monkeypatch.setenv("DATABASE_URL", "postgresql+psycopg://user:pass@localhost:1/test")
    monkeypatch.setenv("KAFKA_BOOTSTRAP_SERVERS", "localhost:1")
    spec = importlib.util.spec_from_file_location("physics_models_consumer_under_test", CONSUMER_PATH)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module.TelemetryConsumer


@pytest.mark.parametrize(
    ("method", "model"),
    [
        ("_insert_comms", SyntheticCommsOutput),
        ("_insert_radiation", SyntheticRadiationOutput),
        ("_insert_packet", SyntheticTelemetryPacket),
    ],
)
def test_insert_writes_every_contract_field(consumer_class, method, model):
    session, message = MagicMock(), MagicMock()
    getattr(consumer_class, method)(None, session, message)
    sql = str(session.execute.call_args.args[0])

    for field in model.model_fields:
        assert f":{field}" in sql
        if field != "timestamp_utc":
            assert f"{field} = EXCLUDED.{field}" in sql
