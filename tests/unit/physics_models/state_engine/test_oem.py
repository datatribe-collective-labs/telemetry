"""Unit tests for the CCSDS OEM loader and interpolation."""

import io
import zipfile
from datetime import UTC, datetime

import numpy as np
import pytest
from physics_models.oem import (
    interpolate_state,
    load_latest_oem_from_store,
    load_oem_asc,
)

OEM_TEMPLATE = """CCSDS_OEM_VERS = 2.0
COMMENT test arc
CREATION_DATE = {created}
ORIGINATOR = TEST

META_START
OBJECT_NAME = EM2
OBJECT_ID = 24
CENTER_NAME = EARTH
REF_FRAME = EME2000
TIME_SYSTEM = UTC
META_STOP

2026-04-02T00:00:00.000 7000.0 0.0 0.0 0.0 7.5 0.0
2026-04-02T00:04:00.000 7010.0 10.0 0.0 0.1 7.5 0.0
2026-04-02T00:08:00.000 7020.0 20.0 0.0 0.2 7.4 0.0
"""


def _make_store(tmp_path):
    """Build a zip-of-zips with two arcs, 04-03 newer than 04-02."""
    store_path = tmp_path / "store.zip"
    with zipfile.ZipFile(store_path, "w") as store:
        for name, created in (("arc_a.zip", "2026-04-02T00:00:00"), ("arc_b.zip", "2026-04-03T00:00:00")):
            buf = io.BytesIO()
            with zipfile.ZipFile(buf, "w") as inner:
                inner.writestr(f"{name.split('.')[0]}.asc", OEM_TEMPLATE.format(created=created))
            store.writestr(name, buf.getvalue())
    return store_path


def test_load_oem_asc_parses_meta_and_states(tmp_path):
    asc = tmp_path / "arc.asc"
    asc.write_text(OEM_TEMPLATE.format(created="2026-04-02T00:00:00"))
    eph = load_oem_asc(asc)
    assert eph.object_name == "EM2"
    assert eph.center_name == "EARTH"
    assert eph.ref_frame == "EME2000"
    assert len(eph.epochs) == 3
    assert eph.start == datetime(2026, 4, 2, tzinfo=UTC)


def test_load_latest_oem_from_store_picks_newest_creation_date(tmp_path):
    eph = load_latest_oem_from_store(_make_store(tmp_path))
    assert eph.creation_date == datetime(2026, 4, 3, tzinfo=UTC)


def test_load_latest_oem_from_store_raises_without_arcs(tmp_path):
    empty = tmp_path / "empty.zip"
    with zipfile.ZipFile(empty, "w"):
        pass
    with pytest.raises(ValueError):
        load_latest_oem_from_store(empty)


def test_interpolate_state_linear_midpoint(tmp_path):
    asc = tmp_path / "arc.asc"
    asc.write_text(OEM_TEMPLATE.format(created="2026-04-02T00:00:00"))
    eph = load_oem_asc(asc)

    pos, vel = interpolate_state(eph, datetime(2026, 4, 2, 0, 2, 0, tzinfo=UTC))
    # halfway between point 1 (7000, 7.5x?) and point 2: x=7005, vx=0.05, vy=7.5
    assert pos == pytest.approx([7005.0, 5.0, 0.0])
    assert vel == pytest.approx([0.05, 7.5, 0.0])


def test_interpolate_state_clamps_outside_arc(tmp_path):
    asc = tmp_path / "arc.asc"
    asc.write_text(OEM_TEMPLATE.format(created="2026-04-02T00:00:00"))
    eph = load_oem_asc(asc)
    pos, _ = interpolate_state(eph, datetime(2026, 5, 1, tzinfo=UTC))
    assert pos[0] == pytest.approx(7020.0)  # clamped to last point


def test_real_store_zip_loads_and_matches_documented_extremes():
    """Integration with the real NASA OEM store committed in docs/overview/."""
    from pathlib import Path

    store = Path("data/oem/all-artemis-ii-oem-files.zip")
    if not store.exists():
        pytest.skip("OEM store zip not present")
    eph = load_latest_oem_from_store(store)
    assert len(eph.epochs) > 3000
    ranges = np.linalg.norm(eph.positions, axis=1)
    assert ranges.max() == pytest.approx(413144, abs=500)  # km, per audit
    assert eph.center_name == "EARTH"
    assert eph.ref_frame == "EME2000"
    mid = datetime.fromtimestamp(float(eph.epochs[0] + eph.epochs[-1]) / 2, UTC)
    pos, vel = interpolate_state(eph, mid)
    assert np.linalg.norm(pos) > 0
    assert np.linalg.norm(vel) > 0
