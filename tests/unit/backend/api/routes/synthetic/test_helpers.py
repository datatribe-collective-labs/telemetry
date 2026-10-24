import pytest
from backend.api.routes.synthetic import (
    _build_where_clause,
    _count_query,
    _execute_query,
    _select_columns,
    _verify_lowercase,
)


class Row:
    def __init__(self, mapping): self._mapping = mapping
class Result:
    def __init__(self, rows=(), scalar_value=0): self.rows=[Row(r) if isinstance(r,dict) else r for r in rows]; self.scalar_value=scalar_value
    def scalar(self): return self.scalar_value
    def first(self): return self.rows[0] if self.rows else None
    def __iter__(self): return iter(self.rows)
class DB:
    def __init__(self, results): self.results=list(results); self.calls=[]
    def execute(self, statement, params=None): self.calls.append((str(statement), params or {})); return self.results.pop(0)

def test_build_where_clause():
    assert _build_where_clause([])==""
    assert _build_where_clause(["a=:a","b=:b"])=="WHERE a=:a AND b=:b"

def test_select_columns():
    assert _select_columns(["timestamp_utc","temp_sun_face_K"]) == 'timestamp_utc AS "timestamp_utc", temp_sun_face_k AS "temp_sun_face_K"'
    assert _select_columns(['event_id::text AS "event_id"']) == 'event_id::text AS "event_id"'

def test_verify_lowercase():
    _verify_lowercase(["timestamp_utc"], "x")
    with pytest.raises(ValueError): _verify_lowercase(["timestamp_UTC"], "x")

def test_execute_query():
    db=DB([Result([{"x":1}])])
    rows=_execute_query(db,"table",["x"],"WHERE x=:x",{"x":1},10,20)
    assert rows==[{"x":1}]
    sql, params=db.calls[0]
    assert "FROM table" in sql and "ORDER BY timestamp_utc" in sql and "LIMIT :limit OFFSET :offset" in sql
    assert params["x"]==1 and params["limit"]==10 and params["offset"]==20
    with pytest.raises(ValueError): _execute_query(db,"t",["x"],"",{},1,0,order_by="timestamp_UTC")

def test_count_query():
    db=DB([Result(scalar_value=None)])
    assert _count_query(db,"t","",{})==0
