"""Ingest JPL SSD Close-Approach Data (CAD) into `close_approaches`.

Source: https://ssd-api.jpl.nasa.gov/doc/cad.html
Fair-use policy: one request at a time, no guaranteed availability - this
module makes a single sequential request per run, no concurrency.

Run directly: `python -m pipelines.ingest.jpl_cad`
"""

import argparse
import os
from dataclasses import dataclass
from datetime import UTC, datetime

import psycopg
import requests

from pipelines.db import get_connection

DEFAULT_BASE_URL = "https://ssd-api.jpl.nasa.gov/cad.api"

CLOSE_APPROACHES_SCHEMA = """
CREATE TABLE IF NOT EXISTS close_approaches (
    des TEXT NOT NULL,
    orbit_id TEXT NOT NULL,
    close_approach_jd DOUBLE PRECISION NOT NULL,
    close_approach_time TIMESTAMPTZ NOT NULL,
    dist_au DOUBLE PRECISION,
    dist_min_au DOUBLE PRECISION,
    dist_max_au DOUBLE PRECISION,
    v_rel_kms DOUBLE PRECISION,
    v_inf_kms DOUBLE PRECISION,
    h_mag DOUBLE PRECISION,
    body TEXT NOT NULL DEFAULT 'Earth',
    ingested_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    PRIMARY KEY (des, orbit_id, close_approach_time)
);
"""

CLOSE_APPROACHES_HYPERTABLE = """
SELECT create_hypertable('close_approaches', 'close_approach_time', if_not_exists => TRUE);
"""


def ensure_close_approaches_table(conn: psycopg.Connection) -> None:
    with conn.cursor() as cur:
        cur.execute(CLOSE_APPROACHES_SCHEMA)
        cur.execute("SELECT 1 FROM pg_extension WHERE extname = 'timescaledb'")
        if cur.fetchone():
            cur.execute(CLOSE_APPROACHES_HYPERTABLE)
        else:
            print("timescaledb extension not installed - using a regular Postgres table.")
    conn.commit()


@dataclass
class CloseApproach:
    des: str
    orbit_id: str
    close_approach_jd: float
    close_approach_time: datetime
    dist_au: float | None
    dist_min_au: float | None
    dist_max_au: float | None
    v_rel_kms: float | None
    v_inf_kms: float | None
    h_mag: float | None
    body: str

    @classmethod
    def from_api_record(cls, record: dict[str, str], default_body: str) -> "CloseApproach":
        return cls(
            des=record["des"],
            orbit_id=record["orbit_id"],
            close_approach_jd=float(record["jd"]),
            close_approach_time=_parse_calendar_date(record["cd"]),
            dist_au=_to_float(record.get("dist")),
            dist_min_au=_to_float(record.get("dist_min")),
            dist_max_au=_to_float(record.get("dist_max")),
            v_rel_kms=_to_float(record.get("v_rel")),
            v_inf_kms=_to_float(record.get("v_inf")),
            h_mag=_to_float(record.get("h")),
            body=record.get("body") or default_body,
        )


def _to_float(value: str | None) -> float | None:
    if value in (None, ""):
        return None
    return float(value)


def _parse_calendar_date(cd: str) -> datetime:
    # CAD "cd" field looks like "2029-Apr-13 21:46" (TDB, treated as UTC here).
    dt = datetime.strptime(cd, "%Y-%b-%d %H:%M")  # noqa: DTZ007 - tz attached on next line
    return dt.replace(tzinfo=UTC)


def fetch_close_approaches(
    date_min: str = "now",
    date_max: str = "+60",
    dist_max: str = "0.05",
    body: str = "Earth",
    base_url: str | None = None,
) -> list[CloseApproach]:
    base_url = base_url or os.environ.get("JPL_CAD_BASE_URL", DEFAULT_BASE_URL)
    params = {
        "date-min": date_min,
        "date-max": date_max,
        "dist-max": dist_max,
        "body": body,
    }
    response = requests.get(base_url, params=params, timeout=30)
    response.raise_for_status()
    payload = response.json()

    fields = payload["fields"]
    rows = payload["data"]
    return [
        CloseApproach.from_api_record(dict(zip(fields, row)), default_body=body)
        for row in rows
    ]


def upsert_close_approaches(conn, records: list[CloseApproach]) -> int:
    if not records:
        return 0

    with conn.cursor() as cur:
        cur.executemany(
            """
            INSERT INTO close_approaches (
                des, orbit_id, close_approach_jd, close_approach_time,
                dist_au, dist_min_au, dist_max_au,
                v_rel_kms, v_inf_kms, h_mag, body
            )
            VALUES (
                %(des)s, %(orbit_id)s, %(close_approach_jd)s, %(close_approach_time)s,
                %(dist_au)s, %(dist_min_au)s, %(dist_max_au)s,
                %(v_rel_kms)s, %(v_inf_kms)s, %(h_mag)s, %(body)s
            )
            ON CONFLICT (des, orbit_id, close_approach_time) DO UPDATE SET
                close_approach_jd = EXCLUDED.close_approach_jd,
                dist_au = EXCLUDED.dist_au,
                dist_min_au = EXCLUDED.dist_min_au,
                dist_max_au = EXCLUDED.dist_max_au,
                v_rel_kms = EXCLUDED.v_rel_kms,
                v_inf_kms = EXCLUDED.v_inf_kms,
                h_mag = EXCLUDED.h_mag,
                body = EXCLUDED.body,
                ingested_at = now()
            """,
            [record.__dict__ for record in records],
        )
    conn.commit()
    return len(records)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--date-min", default=os.environ.get("CAD_DATE_MIN", "now"))
    parser.add_argument("--date-max", default=os.environ.get("CAD_DATE_MAX", "+60"))
    parser.add_argument("--dist-max", default=os.environ.get("CAD_DIST_MAX", "0.05"))
    parser.add_argument("--body", default=os.environ.get("CAD_BODY", "Earth"))
    args = parser.parse_args()

    records = fetch_close_approaches(
        date_min=args.date_min,
        date_max=args.date_max,
        dist_max=args.dist_max,
        body=args.body,
    )

    conn = get_connection()
    try:
        ensure_close_approaches_table(conn)
        count = upsert_close_approaches(conn, records)
    finally:
        conn.close()

    print(f"Upserted {count} close-approach records ({args.date_min} .. {args.date_max}, dist-max={args.dist_max} au).")


if __name__ == "__main__":
    main()