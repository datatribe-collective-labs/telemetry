"""Ingest JPL Horizons ephemeris vectors for Artemis II Orion Spacecraft (-1024) into `orion_ephemeris`.

Source: https://ssd.jpl.nasa.gov/api/horizons.api
Fair-use policy: one request at a time, no guaranteed availability - this
module makes a single sequential request per run, no concurrency.

Run directly: `uv run --package pipelines python -m pipelines.ingest.jpl_orion`
"""

import argparse
import math
import os
import re
from dataclasses import dataclass
from datetime import UTC, datetime

import psycopg
import requests

from pipelines.db import get_connection

DEFAULT_BASE_URL = "https://ssd.jpl.nasa.gov/api/horizons.api"

ORION_EPHEMERIS_SCHEMA = """
CREATE TABLE IF NOT EXISTS orion_ephemeris (
    target_id TEXT NOT NULL DEFAULT '-1024',
    epoch TIMESTAMPTZ NOT NULL,
    jd DOUBLE PRECISION NOT NULL,
    x_km DOUBLE PRECISION,
    y_km DOUBLE PRECISION,
    z_km DOUBLE PRECISION,
    vx_kms DOUBLE PRECISION,
    vy_kms DOUBLE PRECISION,
    vz_kms DOUBLE PRECISION,
    speed_kms DOUBLE PRECISION,
    light_time_s DOUBLE PRECISION,
    range_km DOUBLE PRECISION,
    range_rate_kms DOUBLE PRECISION,
    ingested_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    PRIMARY KEY (target_id, epoch)
);
"""

ORION_EPHEMERIS_HYPERTABLE = """
SELECT create_hypertable('orion_ephemeris', 'epoch', if_not_exists => TRUE);
"""


def ensure_orion_ephemeris_table(conn: psycopg.Connection) -> None:
    with conn.cursor() as cur:
        cur.execute(ORION_EPHEMERIS_SCHEMA)
        cur.execute("SELECT 1 FROM pg_extension WHERE extname = 'timescaledb'")
        if cur.fetchone():
            cur.execute(ORION_EPHEMERIS_HYPERTABLE)
        else:
            print(
                "timescaledb extension not installed - using a regular Postgres table."
            )
    conn.commit()


@dataclass
class OrionRecord:
    target_id: str
    epoch: datetime
    jd: float
    x_km: float | None
    y_km: float | None
    z_km: float | None
    vx_kms: float | None
    vy_kms: float | None
    vz_kms: float | None
    speed_kms: float | None
    light_time_s: float | None
    range_km: float | None
    range_rate_kms: float | None


def _parse_horizons_date(date_str: str) -> datetime:
    clean = date_str.replace("A.D.", "").replace("B.C.", "").strip()
    for fmt in ("%Y-%b-%d %H:%M:%S.%f", "%Y-%b-%d %H:%M:%S", "%Y-%b-%d %H:%M"):
        try:
            dt = datetime.strptime(clean, fmt)
            return dt.replace(tzinfo=UTC)
        except ValueError:
            pass
    return datetime.fromisoformat(clean).replace(tzinfo=UTC)


# Plain-text VECTORS block (VEC_TABLE 3), one epoch per four lines:
#   2461132.583333333 = A.D. 2026-Apr-02 02:00:00.0000 UTC
#    X =-2.472659704823027E+04 Y =-1.316405057554934E+04 Z =-7.164202187370159E+03
#    VX=-1.777351358608879E+00 VY=-3.385561617695174E+00 VZ=-1.830422254985318E+00
#    LT= 9.644690857497219E-02 RG= 2.891405578819219E+04 RR= 3.514867339500120E+00
_EPOCH_LINE = re.compile(r"^\s*(?P<jd>\d+\.\d+)\s*=\s*(?P<date>A\.D\.\s+\S+\s+\S+)")
_VALUE = re.compile(r"\b(X|Y|Z|VX|VY|VZ|LT|RG|RR)\s*=\s*(\S+)")
_VECTOR_KEYS = ("X", "Y", "Z", "VX", "VY", "VZ", "LT", "RG", "RR")


def _parse_vectors_block(block: str) -> list[tuple[float, str, dict[str, float]]]:
    """(jd, calendar date, {X: ..., RR: ...}) per epoch.

    Strict on purpose: an unrecognised line or a missing value raises, so a format
    change on JPL's side fails the ingest instead of storing empty rows (#57).
    """
    epochs: list[tuple[float, str, dict[str, float]]] = []
    for line in block.splitlines():
        if not line.strip():
            continue
        if match := _EPOCH_LINE.match(line):
            epochs.append((float(match["jd"]), match["date"], {}))
        elif (values := _VALUE.findall(line)) and epochs:
            epochs[-1][2].update({key: float(value) for key, value in values})
        else:
            raise ValueError(f"Unrecognised line in Horizons vectors: {line!r}")
    for jd, date, values in epochs:
        missing = [key for key in _VECTOR_KEYS if key not in values]
        if missing:
            raise ValueError(f"Horizons vectors for {date} are missing {missing}")
    return epochs


def fetch_orion_ephemeris(
    command: str = "-1024",
    center: str = "500@399",
    start_time: str = "2026-04-02 02:00",
    stop_time: str = "2026-04-10 23:00",
    step_size: str = "1 h",
    base_url: str | None = None,
) -> list[OrionRecord]:

    base_url = base_url or os.environ.get("JPL_HORIZONS_BASE_URL", DEFAULT_BASE_URL)
    params = {
        "format": "json",
        "COMMAND": f"'{command}'",
        "OBJ_DATA": "YES",
        "MAKE_EPHEM": "YES",
        "EPHEM_TYPE": "VECTORS",
        "OUT_UNITS": "'KM-S'",
        "CENTER": f"'{center}'",
        # Earth mean equator J2000 axes (EME2000), the frame of the NASA OEM files the
        # synthetic state uses. Horizons' default is ECLIPTIC, which differs by a
        # 23.44 deg rotation about X and makes real vs synthetic positions disagree.
        "REF_PLANE": "FRAME",
        "REF_SYSTEM": "ICRF",
        # Stamp rows in UT (VECTORS default is TDB, ~69 s ahead in 2026), matching the
        # UTC synthetic state and the UT-stamped jpl_dsn_geometry OBSERVER tables.
        "TIME_TYPE": "UT",
        "START_TIME": f"'{start_time}'",
        "STOP_TIME": f"'{stop_time}'",
        "STEP_SIZE": f"'{step_size}'",
        # No CSV_FORMAT: since Nov 2026 Horizons' CSV output for VECTORS tables has only
        # the two time columns (no X..RR, #57). The plain-text table still has them all.
    }
    response = requests.get(base_url, params=params, timeout=30)
    response.raise_for_status()
    data = response.json()

    if "error" in data:
        raise RuntimeError(f"JPL Horizons API Error: {data['error']}")

    result_text = data.get("result", "")
    if "$$SOE" not in result_text or "$$EOE" not in result_text:
        print("No ephemeris data markers ($$SOE / $$EOE) found in API response.")
        return []

    block = result_text.split("$$SOE", 1)[1].split("$$EOE")[0]
    return [
        OrionRecord(
            target_id=command.strip("'"),
            epoch=_parse_horizons_date(date),
            jd=jd,
            x_km=v["X"],
            y_km=v["Y"],
            z_km=v["Z"],
            vx_kms=v["VX"],
            vy_kms=v["VY"],
            vz_kms=v["VZ"],
            speed_kms=math.sqrt(v["VX"] ** 2 + v["VY"] ** 2 + v["VZ"] ** 2),
            light_time_s=v["LT"],
            range_km=v["RG"],
            range_rate_kms=v["RR"],
        )
        for jd, date, v in _parse_vectors_block(block)
    ]


def upsert_orion_ephemeris(conn: psycopg.Connection, records: list[OrionRecord]) -> int:
    if not records:
        return 0

    with conn.cursor() as cur:
        cur.executemany(
            """
            INSERT INTO orion_ephemeris (
                target_id, epoch, jd, x_km, y_km, z_km,
                vx_kms, vy_kms, vz_kms, speed_kms,
                light_time_s, range_km, range_rate_kms
            )
            VALUES (
                %(target_id)s, %(epoch)s, %(jd)s, %(x_km)s, %(y_km)s, %(z_km)s,
                %(vx_kms)s, %(vy_kms)s, %(vz_kms)s, %(speed_kms)s,
                %(light_time_s)s, %(range_km)s, %(range_rate_kms)s
            )
            ON CONFLICT (target_id, epoch) DO UPDATE SET
                jd = EXCLUDED.jd,
                x_km = EXCLUDED.x_km,
                y_km = EXCLUDED.y_km,
                z_km = EXCLUDED.z_km,
                vx_kms = EXCLUDED.vx_kms,
                vy_kms = EXCLUDED.vy_kms,
                vz_kms = EXCLUDED.vz_kms,
                speed_kms = EXCLUDED.speed_kms,
                light_time_s = EXCLUDED.light_time_s,
                range_km = EXCLUDED.range_km,
                range_rate_kms = EXCLUDED.range_rate_kms,
                ingested_at = now()
            """,
            [record.__dict__ for record in records],
        )
    conn.commit()
    return len(records)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--command", default=os.environ.get("HORIZONS_COMMAND", "-1024")
    )
    parser.add_argument(
        "--center", default=os.environ.get("HORIZONS_CENTER", "500@399")
    )
    parser.add_argument(
        "--start-time", default=os.environ.get("HORIZONS_START", "2026-04-02 02:00")
    )
    parser.add_argument(
        "--stop-time", default=os.environ.get("HORIZONS_STOP", "2026-04-10 23:00")
    )

    parser.add_argument("--step-size", default=os.environ.get("HORIZONS_STEP", "1 h"))
    args = parser.parse_args()

    records = fetch_orion_ephemeris(
        command=args.command,
        center=args.center,
        start_time=args.start_time,
        stop_time=args.stop_time,
        step_size=args.step_size,
    )

    conn = get_connection()
    try:
        ensure_orion_ephemeris_table(conn)
        count = upsert_orion_ephemeris(conn, records)
    finally:
        conn.close()

    print(
        f"Upserted {count} Orion ephemeris records ({args.start_time} .. {args.stop_time})."
    )


if __name__ == "__main__":
    main()
