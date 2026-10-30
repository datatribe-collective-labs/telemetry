import sys
import types

import pytest
from fastapi.testclient import TestClient

_db = types.ModuleType("backend.db")
def get_db():
    raise RuntimeError("test dependency must be overridden")
_db.get_db = get_db
sys.modules["backend.db"] = _db
from datetime import UTC

from backend.api import app


class Row:
    def __init__(self, mapping): self._mapping = mapping

class Result:
    def __init__(self, rows=(), scalar_value=0): self.rows=[Row(r) if isinstance(r,dict) else r for r in rows]; self.scalar_value=scalar_value
    def scalar(self): return self.scalar_value
    def first(self): return self.rows[0] if self.rows else None
    def __iter__(self): return iter(self.rows)

class FakeSession:
    def __init__(self, results=()): self.results=list(results); self.calls=[]
    def execute(self, statement, params=None):
        self.calls.append((str(statement), params or {}))
        return self.results.pop(0) if self.results else Result()
    def close(self): pass

@pytest.fixture
def fake_session(): return FakeSession()

@pytest.fixture
def client(fake_session):
    def override(): yield fake_session
    app.dependency_overrides[get_db]=override
    try: yield TestClient(app)
    finally: app.dependency_overrides.clear()

def make_row(columns):
    from datetime import datetime
    out = {}
    for c in columns:
        if ' AS ' in c:
            key = c.split(' AS ',1)[1].strip('"')
        else:
            key = c
        if key == 'timestamp_utc' or key == 'epoch' or key == 'close_approach_time' or key in {'start_time','end_time','event_time','fetched_at'}:
            out[key] = datetime(2026, 4, 1, 12, 0, tzinfo=UTC)
        elif key == 'event_id': out[key] = '11111111-1111-1111-1111-111111111111'
        elif key in {'dsn_visibility','heater_active','sep_event_active','all_nominal','visible'}: out[key] = False
        elif key in {'eclipse_state'}: out[key] = 'SUNLIT'
        elif key in {'thermal_state'} or key in {'power_state'} or key in {'comm_state'}: out[key] = 'NOMINAL'
        elif key == 'severity': out[key] = 'INFO'
        elif key == 'spacecraft_id': out[key] = 'ORION_EM2'
        elif key in {'site','complex','proton_satellite','target_id','orbit_id','des','body','source_url','event_type','anomaly_type','description','field_name','contract_reference','suggested_cause','mission_phase'}: out[key] = 'TEST'
        elif key == 'payload': out[key] = {'test': True}
        elif key == 'detection_layer': out[key] = 1
        else: out[key] = 1.234
    return out

@pytest.fixture
def row_factory(): return make_row

@pytest.fixture
def result_factory(): return Result
