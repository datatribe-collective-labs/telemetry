"""Unit tests for pipelines.ingest.nasa_oem (no DB, local synthetic data)."""

import io
import zipfile

import pytest
from pipelines.ingest.nasa_oem import parse_oem_asc, read_store

OEM_TEXT = """CCSDS_OEM_VERS = 2.0
CREATION_DATE = 2026-04-02T14:06:23
META_START
OBJECT_NAME = EM2
CENTER_NAME = EARTH
REF_FRAME = EME2000
META_STOP

2026-04-02T01:57:37.084 -24468.0 -12677.9 -6901.3 -1.83 -3.41 -1.84
2026-04-02T02:01:37.084 -24588.0 -12901.9 -7022.4 -1.81 -3.40 -1.83
"""


def test_parse_oem_asc_extracts_states_with_derived_scalars():
    rows = parse_oem_asc(OEM_TEXT, "test_arc")
    assert len(rows) == 2
    r = rows[0]
    assert r.arc_id == "test_arc"
    assert r.epoch.isoformat() == "2026-04-02T01:57:37.084000+00:00"
    assert r.x_km == -24468.0
    assert r.range_km == pytest.approx(28408.5, abs=0.5)
    assert r.speed_kms == pytest.approx(4.285, abs=0.01)


def test_parse_oem_asc_ignores_headers_and_comments():
    assert len(parse_oem_asc("CCSDS_OEM_VERS = 2.0\nCOMMENT nothing\n", "x")) == 0


def test_read_store_flattens_nested_zips(tmp_path):
    store = tmp_path / "store.zip"
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as inner:
        inner.writestr("arc.asc", OEM_TEXT)
    with zipfile.ZipFile(store, "w") as outer:
        outer.writestr("2026_04_02_arc.zip", buf.getvalue())
    arcs = read_store(store)
    assert len(arcs) == 1
    assert arcs[0][0] == "2026_04_02_arc"
    assert "EM2" in arcs[0][1]


def test_read_store_raises_on_empty(tmp_path):
    store = tmp_path / "empty.zip"
    with zipfile.ZipFile(store, "w"):
        pass
    with pytest.raises(ValueError):
        read_store(store)
