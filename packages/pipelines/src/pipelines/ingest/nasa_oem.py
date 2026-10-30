"""Ingest NASA CCSDS OEM ephemeris arcs (Artemis II / EM-2) into `oem_state_vectors`.

Source: data/oem/all-artemis-ii-oem-files.zip — a store zip containing nested
per-arc zips, each with one CCSDS OEM v2.0 .asc file (Earth-centered EME2000,
UTC, km / km/s). Every arc is ingested separately with its filename stem as
`arc_id` so planning-history revisions stay queryable side by side.

No network access: this is a file ingest, unlike the JPL/NASA API ingests.

Run directly: `uv run --package pipelines python -m pipelines.ingest.nasa_oem`
"""

import argparse
import io
import re
import zipfile
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path

import numpy as np
import psycopg

from pipelines.db import get_connection

DEFAULT_STORE_ZIP = "data/oem/all-artemis-ii-oem-files.zip"

OEM_TABLE_SCHEMA = """
CREATE TABLE IF NOT EXISTS oem_state_vectors (
    arc_id TEXT NOT NULL,
    epoch TIMESTAMPTZ NOT NULL,
    x_km DOUBLE PRECISION,
    y_km DOUBLE PRECISION,
    z_km DOUBLE PRECISION,
    vx_kms DOUBLE PRECISION,
    vy_kms DOUBLE PRECISION,
    vz_kms DOUBLE PRECISION,
    range_km DOUBLE PRECISION,
    speed_kms DOUBLE PRECISION,
    ingested_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    PRIMARY KEY (arc_id, epoch)
);
"""

OEM_HYPERTABLE = """
SELECT create_hypertable('oem_state_vectors', 'epoch', if_not_exists => TRUE);
"""

UPSERT_OEM_STATE = """
INSERT INTO oem_state_vectors
    (arc_id, epoch, x_km, y_km, z_km, vx_kms, vy_kms, vz_kms, range_km, speed_kms)
VALUES (%(arc_id)s, %(epoch)s, %(x_km)s, %(y_km)s, %(z_km)s,
        %(vx_kms)s, %(vy_kms)s, %(vz_kms)s, %(range_km)s, %(speed_kms)s)
ON CONFLICT (arc_id, epoch) DO UPDATE SET
    x_km = EXCLUDED.x_km,
    y_km = EXCLUDED.y_km,
    z_km = EXCLUDED.z_km,
    vx_kms = EXCLUDED.vx_kms,
    vy_kms = EXCLUDED.vy_kms,
    vz_kms = EXCLUDED.vz_kms,
    range_km = EXCLUDED.range_km,
    speed_kms = EXCLUDED.speed_kms;
"""

_STATE_LINE = re.compile(
    r"^(\d{4}-\d{2}-\d{2}T[\d:.]+)\s+(\S+)\s+(\S+)\s+(\S+)\s+(\S+)\s+(\S+)\s+(\S+)\s*$"
)


@dataclass(frozen=True)
class OemStateRow:
    arc_id: str
    epoch: datetime
    x_km: float
    y_km: float
    z_km: float
    vx_kms: float
    vy_kms: float
    vz_kms: float
    range_km: float
    speed_kms: float


def parse_oem_asc(text: str, arc_id: str) -> list[OemStateRow]:
    """Parse one CCSDS OEM .asc file into state rows (derived range/speed added)."""
    rows: list[OemStateRow] = []
    for line in text.splitlines():
        m = _STATE_LINE.match(line.strip())
        if not m:
            continue
        ts = datetime.fromisoformat(m.group(1)).replace(tzinfo=UTC)
        x, y, z, vx, vy, vz = map(float, m.groups()[1:])
        rows.append(
            OemStateRow(
                arc_id=arc_id,
                epoch=ts,
                x_km=x, y_km=y, z_km=z,
                vx_kms=vx, vy_kms=vy, vz_kms=vz,
                range_km=float(np.linalg.norm([x, y, z])),
                speed_kms=float(np.linalg.norm([vx, vy, vz])),
            )
        )
    return rows


def read_store(store_zip: str | Path) -> list[tuple[str, str]]:
    """Return (arc_id, asc_text) pairs from the zip-of-zips store.

    Only CCSDS OEM files are ingested. One member ("2026.04.10 - Post-RTC3 to EI")
    is a legacy PROP_MAN 11.0 entry-arc (M50 epoch seconds, FT/FPS units) and is
    skipped with a warning — it is not CCSDS OEM v2.0.
    """
    arcs: list[tuple[str, str]] = []
    with zipfile.ZipFile(store_zip) as store:
        for member in store.namelist():
            if not member.lower().endswith(".zip"):
                continue
            arc_id = Path(member).stem
            with zipfile.ZipFile(io.BytesIO(store.read(member))) as inner:
                texts = [
                    inner.read(name).decode("utf-8", "replace")
                    for name in inner.namelist()
                    if not name.endswith("/")
                ]
                ccsds = [t for t in texts if "CCSDS_OEM_VERS" in t]
                if not ccsds:
                    print(f"WARNING: skipping '{member}' — no CCSDS OEM content (unsupported format)")
                    continue
                arcs.append((arc_id, ccsds[0]))
    if not arcs:
        raise ValueError(f"No CCSDS OEM content found in {store_zip}")
    return arcs


def ensure_oem_table(conn: psycopg.Connection) -> None:
    with conn.cursor() as cur:
        cur.execute(OEM_TABLE_SCHEMA)
        cur.execute(OEM_HYPERTABLE)
    conn.commit()


def upsert_oem_states(conn: psycopg.Connection, rows: list[OemStateRow]) -> int:
    with conn.cursor() as cur:
        cur.executemany(UPSERT_OEM_STATE, [r.__dict__ for r in rows])
    conn.commit()
    return len(rows)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--store", default=DEFAULT_STORE_ZIP, help="Path to OEM store zip")
    args = parser.parse_args()

    arcs = read_store(args.store)
    with get_connection() as conn:
        ensure_oem_table(conn)
        total = 0
        for arc_id, text in arcs:  # sequential; local files, but same discipline as API ingests
            rows = parse_oem_asc(text, arc_id)
            total += upsert_oem_states(conn, rows)
            print(f"Ingested arc '{arc_id}': {len(rows)} state vectors")
    print(f"Done. {total} state vectors across {len(arcs)} arcs.")


if __name__ == "__main__":
    main()
