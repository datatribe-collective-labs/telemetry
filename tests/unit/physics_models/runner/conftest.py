"""Fixtures for unit tests of physics_models.runner."""

from datetime import datetime, timedelta
from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest
from physics_models import runner as runner_module
from physics_models.config import PhysicsModelsConfig, StateEngineConfig

LIFTOFF = datetime.fromisoformat("2026-04-01T22:35:00Z")
OEM_END_MET_S = 1000.0


@pytest.fixture
def make_runner(monkeypatch):
    """Build a SimulatorRunner with no Kafka and a fake OEM arc ending at OEM_END_MET_S.

    Pass `oem=False` for placeholder-orbit mode (no OEM arc).
    """
    monkeypatch.setattr(runner_module, "PhysicsModelsKafkaProducer", MagicMock())

    def _make(*, oem: bool = True, **config) -> runner_module.SimulatorRunner:
        fake_arc = SimpleNamespace(stop=LIFTOFF + timedelta(seconds=OEM_END_MET_S)) if oem else None
        monkeypatch.setattr(runner_module.SimulatorRunner, "_load_oem", lambda self, cfg: fake_arc)
        cfg = PhysicsModelsConfig(
            state_engine=StateEngineConfig(liftoff_utc=LIFTOFF.isoformat()), **config
        )
        return runner_module.SimulatorRunner(cfg)

    return _make


@pytest.fixture
def oem_end_met_s() -> float:
    """MET (s) at which make_runner's fake OEM arc ends."""
    return OEM_END_MET_S
