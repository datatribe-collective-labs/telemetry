"""Ingest JPL Horizons ephemeris vectors for the Moon (301) into `moon_ephemeris`.

The Digital Twin dashboard draws the Moon on Orion's trajectory map, so the rows
use the same Earth-centred EME2000 axes and UT time stamps as `orion_ephemeris`
(see `jpl_orion` for why REF_PLANE=FRAME and TIME_TYPE=UT matter).

Source: https://ssd.jpl.nasa.gov/api/horizons.api
Fair-use policy: one request at a time, no guaranteed availability - this
module makes a single sequential request per run, no concurrency.

Run directly: `uv run --package pipelines python -m pipelines.ingest.jpl_moon`
"""

import argparse
import os
from dataclasses import dataclass
from datetime import datetime

import psycopg

from pipelines.db import get_connection

# Same Horizons VECTORS request and parsing as Orion; only the target differs.
from pipelines.ingest.jpl_orion import fetch_orion_ephemeris

MOON_ID = "301"
# The whole flight, liftoff (Apr 1 22:35 UTC) to after splashdown; wider than
# Orion's arc so the Moon is on the map for every mission time the slider allows.
DEFAULT_START = "2026-04-01 22:00"
DEFAULT_STOP = "2026-04-11 00:00"

MOON_EPHEMERIS_SCHEMA = """
CREATE TABLE IF NOT EXISTS moon_ephemeris (
    epoch TIMESTAMPTZ NOT NULL PRIMARY KEY,
    jd DOUBLE PRECISION NOT NULL,
    x_km DOUBLE PRECISION,
    y_km DOUBLE PRECISION,
    z_km DOUBLE PRECISION,
    vx_kms DOUBLE PRECISION,
    vy_kms DOUBLE PRECISION,
    vz_kms DOUBLE PRECISION,
    range_km DOUBLE PRECISION,
    ingested_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
"""

MOON_EPHEMERIS_HYPERTABLE = """
SELECT create_hypertable('moon_ephemeris', 'epoch', if_not_exists => TRUE);
"""


def ensure_moon_ephemeris_table(conn: psycopg.Connection) -> None:
    with conn.cursor() as cur:
        cur.execute(MOON_EPHEMERIS_SCHEMA)
        cur.execute("SELECT 1 FROM pg_extension WHERE extname = 'timescaledb'")
        if cur.fetchone():
            cur.execute(MOON_EPHEMERIS_HYPERTABLE)
        else:
            print("timescaledb extension not installed - using a regular Postgres table.")
    conn.commit()


@dataclass
class MoonRecord:
    epoch: datetime
    jd: float
    x_km: float | None
    y_km: float | None
    z_km: float | None
    vx_kms: float | None
    vy_kms: float | None
    vz_kms: float | None
    range_km: float | None


def fetch_moon_ephemeris(
    start_time: str = DEFAULT_START,
    stop_time: str = DEFAULT_STOP,
    step_size: str = "1 h",
    base_url: str | None = None,
) -> list[MoonRecord]:
    """Earth-centred (500@399) EME2000 position/velocity of the Moon, UT time stamps."""
    rows = fetch_orion_ephemeris(
        command=MOON_ID,
        center="500@399",
        start_time=start_time,
        stop_time=stop_time,
        step_size=step_size,
        base_url=base_url,
    )
    return [
        MoonRecord(
            epoch=r.epoch, jd=r.jd, x_km=r.x_km, y_km=r.y_km, z_km=r.z_km,
            vx_kms=r.vx_kms, vy_kms=r.vy_kms, vz_kms=r.vz_kms, range_km=r.range_km,
        )
        for r in rows
    ]


def upsert_moon_ephemeris(conn: psycopg.Connection, records: list[MoonRecord]) -> int:
    if not records:
        return 0

    with conn.cursor() as cur:
        cur.executemany(
            """
            INSERT INTO moon_ephemeris (
                epoch, jd, x_km, y_km, z_km, vx_kms, vy_kms, vz_kms, range_km
            )
            VALUES (
                %(epoch)s, %(jd)s, %(x_km)s, %(y_km)s, %(z_km)s,
                %(vx_kms)s, %(vy_kms)s, %(vz_kms)s, %(range_km)s
            )
            ON CONFLICT (epoch) DO UPDATE SET
                jd = EXCLUDED.jd,
                x_km = EXCLUDED.x_km,
                y_km = EXCLUDED.y_km,
                z_km = EXCLUDED.z_km,
                vx_kms = EXCLUDED.vx_kms,
                vy_kms = EXCLUDED.vy_kms,
                vz_kms = EXCLUDED.vz_kms,
                range_km = EXCLUDED.range_km,
                ingested_at = now()
            """,
            [record.__dict__ for record in records],
        )
    conn.commit()
    return len(records)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--start-time", default=os.environ.get("HORIZONS_MOON_START", DEFAULT_START))
    parser.add_argument("--stop-time", default=os.environ.get("HORIZONS_MOON_STOP", DEFAULT_STOP))
    parser.add_argument("--step-size", default=os.environ.get("HORIZONS_STEP", "1 h"))
    args = parser.parse_args()

    records = fetch_moon_ephemeris(
        start_time=args.start_time, stop_time=args.stop_time, step_size=args.step_size
    )

    conn = get_connection()
    try:
        ensure_moon_ephemeris_table(conn)
        count = upsert_moon_ephemeris(conn, records)
    finally:
        conn.close()

    print(f"Upserted {count} Moon ephemeris records ({args.start_time} .. {args.stop_time}).")


if __name__ == "__main__":
    main()
