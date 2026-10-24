"""Ingest JPL Horizons ephemeris vectors for Artemis II Orion Spacecraft (-1024) into `orion_ephemeris`.

Source: https://ssd.jpl.nasa.gov/api/horizons.api
Fair-use policy: one request at a time, no guaranteed availability - this
module makes a single sequential request per run, no concurrency.

Run directly: `uv run --package pipelines python -m pipelines.ingest.jpl_orion`
"""

import argparse
import io
import math
import os
from dataclasses import dataclass
from datetime import UTC, datetime

import pandas as pd
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


def _to_float(val: object) -> float | None:
    if val is None or pd.isna(val) or val == "":
        return None
    try:
        return float(val)
    except (ValueError, TypeError):
        return None


def _parse_horizons_date(date_str: str) -> datetime:
    clean = date_str.replace("A.D.", "").replace("B.C.", "").strip()
    for fmt in ("%Y-%b-%d %H:%M:%S.%f", "%Y-%b-%d %H:%M:%S", "%Y-%b-%d %H:%M"):
        try:
            dt = datetime.strptime(clean, fmt)
            return dt.replace(tzinfo=UTC)
        except ValueError:
            pass
    return datetime.fromisoformat(clean).replace(tzinfo=UTC)


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
        "START_TIME": f"'{start_time}'",
        "STOP_TIME": f"'{stop_time}'",
        "STEP_SIZE": f"'{step_size}'",
        "CSV_FORMAT": "YES",
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

    csv_data = result_text.split("$$SOE")[1].split("$$EOE")[0].strip()
    df = pd.read_csv(io.StringIO(csv_data), skipinitialspace=True)
    df = df.dropna(axis=1, how="all")
    df.columns = [col.strip() for col in df.columns]

    def _get_col(candidates: list[str], default_idx: int) -> str:
        for c in df.columns:
            for cand in candidates:
                if c == cand or c.startswith(cand):
                    return c
        for c in df.columns:
            if any(cand in c for cand in candidates):
                return c
        if default_idx < len(df.columns):
            return df.columns[default_idx]
        raise ValueError(
            f"Could not find matching column for {candidates} in {df.columns.tolist()}"
        )

    jd_col = _get_col(["JDTDB", "JD"], 0)
    date_col = _get_col(["Calendar Date", "Calendar", "Date", "TDB"], 1)
    x_col = _get_col(["X"], 2)
    y_col = _get_col(["Y"], 3)
    z_col = _get_col(["Z"], 4)
    vx_col = _get_col(["VX"], 5)
    vy_col = _get_col(["VY"], 6)
    vz_col = _get_col(["VZ"], 7)
    lt_col = _get_col(["LT"], 8)
    rg_col = _get_col(["RG"], 9)
    rr_col = _get_col(["RR"], 10)

    records: list[OrionRecord] = []
    for _, row in df.iterrows():
        vx = _to_float(row[vx_col])
        vy = _to_float(row[vy_col])
        vz = _to_float(row[vz_col])
        speed = math.sqrt(vx**2 + vy**2 + vz**2) if None not in (vx, vy, vz) else None

        rec = OrionRecord(
            target_id=command.strip("'"),
            epoch=_parse_horizons_date(str(row[date_col])),
            jd=_to_float(row[jd_col]) or 0.0,
            x_km=_to_float(row[x_col]),
            y_km=_to_float(row[y_col]),
            z_km=_to_float(row[z_col]),
            vx_kms=vx,
            vy_kms=vy,
            vz_kms=vz,
            speed_kms=speed,
            light_time_s=_to_float(row[lt_col]),
            range_km=_to_float(row[rg_col]),
            range_rate_kms=_to_float(row[rr_col]),
        )
        records.append(rec)

    return records


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
