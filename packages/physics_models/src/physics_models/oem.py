"""CCSDS OEM ephemeris loader and interpolation for the state engine.

Parses NASA/JSC CCSDS OEM v2.0 files (e.g. the Artemis II planning arcs in
data/oem/all-artemis-ii-oem-files.zip). Files are Earth-centered, EME2000,
UTC, km / km/s. The store zip contains nested per-arc zips, each with one .asc
file; the newest arc (by CREATION_DATE) is selected by default.
"""

from __future__ import annotations

import io
import zipfile
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path

import numpy as np


@dataclass
class OemEphemeris:
    """Parsed OEM arc: sorted epochs and state vectors (EME2000, km / km/s)."""

    epochs: np.ndarray          # float64 unix seconds, sorted
    positions: np.ndarray       # (N, 3) km
    velocities: np.ndarray      # (N, 3) km/s
    creation_date: datetime
    object_name: str = "EM2"
    center_name: str = "EARTH"
    ref_frame: str = "EME2000"

    @property
    def start(self) -> datetime:
        return datetime.fromtimestamp(float(self.epochs[0]), UTC)

    @property
    def stop(self) -> datetime:
        return datetime.fromtimestamp(float(self.epochs[-1]), UTC)


def _parse_oem_text(text: str) -> tuple[dict[str, str], list[tuple[datetime, np.ndarray, np.ndarray]]]:
    meta: dict[str, str] = {}
    in_meta = False
    rows: list[tuple[datetime, np.ndarray, np.ndarray]] = []
    created = None
    for line in text.splitlines():
        line = line.strip()
        if not line:
            continue
        if line == "META_START":
            in_meta = True
            continue
        if line == "META_STOP":
            in_meta = False
            continue
        if in_meta:
            if "=" in line:
                k, _, v = line.partition("=")
                meta[k.strip()] = v.strip()
            continue
        if line.startswith(("CCSDS_OEM_VERS", "COMMENT")):
            continue
        if line.startswith("CREATION_DATE"):
            created = line.partition("=")[2].strip()
            continue
        parts = line.split()
        if len(parts) == 7:
            try:
                ts = datetime.fromisoformat(parts[0]).replace(tzinfo=UTC)
                vals = [float(p) for p in parts[1:]]
            except ValueError:
                continue
            rows.append((ts, np.array(vals[:3]), np.array(vals[3:])))
    if created:
        meta["CREATION_DATE"] = created
    return meta, rows


def _sort_and_build(meta: dict[str, str], rows) -> OemEphemeris:
    rows.sort(key=lambda r: r[0])
    epochs = np.array([r[0].timestamp() for r in rows], dtype=float)
    positions = np.stack([r[1] for r in rows])
    velocities = np.stack([r[2] for r in rows])
    created = meta.get("CREATION_DATE", "1970-01-01T00:00:00")
    return OemEphemeris(
        epochs=epochs,
        positions=positions,
        velocities=velocities,
        creation_date=datetime.fromisoformat(created).replace(tzinfo=UTC),
        object_name=meta.get("OBJECT_NAME", "EM2"),
        center_name=meta.get("CENTER_NAME", "EARTH"),
        ref_frame=meta.get("REF_FRAME", "EME2000"),
    )


def load_oem_asc(path: str | Path) -> OemEphemeris:
    """Load a single CCSDS OEM .asc file."""
    return _sort_and_build(*_parse_oem_text(Path(path).read_text()))


def load_latest_oem_from_store(store_zip: str | Path) -> OemEphemeris:
    """Load the newest arc from a zip-of-zips store (e.g. all-artemis-ii-oem-files.zip).

    Each member of the store zip is itself a zip containing one .asc OEM file.
    Selection is by the CREATION_DATE header of the parsed arc (latest wins).
    """
    best: OemEphemeris | None = None
    with zipfile.ZipFile(store_zip) as store:
        for member in store.namelist():
            if not member.lower().endswith(".zip"):
                continue
            with zipfile.ZipFile(io.BytesIO(store.read(member))) as inner:
                for name in inner.namelist():
                    if not name.lower().endswith(".asc"):
                        continue
                    eph = _sort_and_build(*_parse_oem_text(inner.read(name).decode("utf-8", "replace")))
                    if best is None or eph.creation_date > best.creation_date:
                        best = eph
    if best is None:
        raise ValueError(f"No OEM .asc files found in {store_zip}")
    return best


def interpolate_state(eph: OemEphemeris, t: datetime) -> tuple[np.ndarray, np.ndarray]:
    """Linearly interpolate position (km) and velocity (km/s) at time t (UTC).

    Times just outside the arc edges are clamped to the nearest endpoint
    (documented behaviour: OEM arcs are planning segments, not for propagation).
    """
    t = t.astimezone(UTC) if t.tzinfo else t.replace(tzinfo=UTC)
    x = np.interp(t.timestamp(), eph.epochs, eph.positions[:, 0])
    y = np.interp(t.timestamp(), eph.epochs, eph.positions[:, 1])
    z = np.interp(t.timestamp(), eph.epochs, eph.positions[:, 2])
    vx = np.interp(t.timestamp(), eph.epochs, eph.velocities[:, 0])
    vy = np.interp(t.timestamp(), eph.epochs, eph.velocities[:, 1])
    vz = np.interp(t.timestamp(), eph.epochs, eph.velocities[:, 2])
    return np.array([x, y, z]), np.array([vx, vy, vz])
