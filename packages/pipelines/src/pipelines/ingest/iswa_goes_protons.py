"""Ingest GOES integral proton flux from NASA CCMC iSWA into `goes_integral_protons`.

Source: https://iswa.gsfc.nasa.gov/IswaSystemWebApp/hapi/
Dataset: `goesp_part_flux_P5M` - "GOES-Primary RT Solar Particle and Electron
Flux (5-minute)", served over HAPI 2.0 as JSON.

This is NOAA's *real-time* GOES product (provisional, not the reprocessed
science-quality archive). The satellite behind the "primary" proton feed can
change over time, so it is stored per row in `proton_satellite`. Electron
channels are not ingested.

All `p*_pfu` columns are integral flux in pfu (protons / cm^2 s sr); HAPI fill
values are stored as NULL. One row per 5-minute sample (`time` primary key), so
re-running any range updates rows in place.

Fair-use: a single sequential request per run, no concurrency.

Run directly, for example:
    uv run --package pipelines python -m pipelines.ingest.iswa_goes_protons \
        --start 2026-04-01T00:00:00Z --end 2026-04-12T00:00:00Z
"""

import argparse
import os
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any

import psycopg
import requests

from pipelines.db import get_connection

DEFAULT_BASE_URL = "https://iswa.gsfc.nasa.gov/IswaSystemWebApp/hapi"
DATASET_ID = "goesp_part_flux_P5M"
# Covers the Artemis II flight (liftoff 2026-04-01T22:35Z, splashdown 2026-04-11T00:07Z).
DEFAULT_START = "2026-04-01T00:00:00Z"
DEFAULT_END = "2026-04-12T00:00:00Z"

# HAPI status codes: 1200 = OK, 1201 = OK but no data for the time range.
HAPI_OK_CODES = (1200, 1201)

# HAPI parameter name -> table column. HAPI requires requested parameters to be
# listed in the dataset's own order (error 1411 otherwise) - keep this mapping
# in the order of the dataset's /info response.
PROTON_PARAMETERS = {
    "P1": "p1_pfu",
    "P5": "p5_pfu",
    "P10": "p10_pfu",
    "P30": "p30_pfu",
    "P50": "p50_pfu",
    "P100": "p100_pfu",
    "P60": "p60_pfu",
    "P500": "p500_pfu",
}
SATELLITE_PARAMETER = "satelliteProton"
REQUESTED_PARAMETERS = (*PROTON_PARAMETERS, SATELLITE_PARAMETER)

GOES_INTEGRAL_PROTONS_SCHEMA = """
CREATE TABLE IF NOT EXISTS goes_integral_protons (
    time TIMESTAMPTZ NOT NULL PRIMARY KEY,
    proton_satellite TEXT,
    p1_pfu DOUBLE PRECISION,
    p5_pfu DOUBLE PRECISION,
    p10_pfu DOUBLE PRECISION,
    p30_pfu DOUBLE PRECISION,
    p50_pfu DOUBLE PRECISION,
    p60_pfu DOUBLE PRECISION,
    p100_pfu DOUBLE PRECISION,
    p500_pfu DOUBLE PRECISION,
    ingested_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
"""

GOES_INTEGRAL_PROTONS_HYPERTABLE = """
SELECT create_hypertable('goes_integral_protons', 'time', if_not_exists => TRUE);
"""


def ensure_goes_integral_protons_table(conn: psycopg.Connection) -> None:
    with conn.cursor() as cur:
        cur.execute(GOES_INTEGRAL_PROTONS_SCHEMA)
        cur.execute("SELECT 1 FROM pg_extension WHERE extname = 'timescaledb'")
        if cur.fetchone():
            cur.execute(GOES_INTEGRAL_PROTONS_HYPERTABLE)
        else:
            print("timescaledb extension not installed - using a regular Postgres table.")
    conn.commit()


@dataclass
class GoesProtonFlux:
    time: datetime
    proton_satellite: str | None
    p1_pfu: float | None
    p5_pfu: float | None
    p10_pfu: float | None
    p30_pfu: float | None
    p50_pfu: float | None
    p60_pfu: float | None
    p100_pfu: float | None
    p500_pfu: float | None

    @classmethod
    def from_api_row(cls, row: dict[str, Any], fills: dict[str, str | None]) -> "GoesProtonFlux":
        satellite = row.get(SATELLITE_PARAMETER)
        return cls(
            time=_parse_hapi_time(row["Time"]),
            proton_satellite=None if _is_fill(satellite, fills.get(SATELLITE_PARAMETER)) else str(satellite),
            **{
                column: _to_flux(row.get(name), fills.get(name))
                for name, column in PROTON_PARAMETERS.items()
            },
        )


def _is_fill(value: Any, fill: str | None) -> bool:
    # HAPI fill values are strings in /info ("-100000", "null"); data values may
    # be numbers, so compare numerically when both sides are numeric.
    if value is None or value == "":
        return True
    if fill is None:
        return False
    if str(value) == fill:
        return True
    try:
        return float(value) == float(fill)
    except (TypeError, ValueError):
        return False


def _to_flux(value: Any, fill: str | None) -> float | None:
    if _is_fill(value, fill):
        return None
    return float(value)


def _parse_hapi_time(value: str) -> datetime:
    # HAPI isotime, e.g. "2026-04-01T22:00:00Z" or "2026-04-01T22:00:00.000Z".
    return datetime.fromisoformat(value).astimezone(UTC)


def _raise_for_hapi_status(response: requests.Response) -> None:
    # HAPI reports errors in a JSON "status" object, often alongside an HTTP 4xx;
    # prefer its message over a bare HTTPError.
    try:
        status = response.json().get("status") or {}
    except ValueError:
        status = {}
    code = status.get("code")
    if response.ok and code in HAPI_OK_CODES:
        return
    if code is not None:
        raise RuntimeError(f"iSWA HAPI error {code}: {status.get('message', '')}")
    response.raise_for_status()
    raise RuntimeError("iSWA HAPI response has no status object")


def fetch_goes_integral_protons(
    start: str = DEFAULT_START,
    end: str = DEFAULT_END,
    base_url: str | None = None,
) -> list[GoesProtonFlux]:
    base_url = base_url or os.environ.get("ISWA_HAPI_BASE_URL", DEFAULT_BASE_URL)
    params = {
        "id": DATASET_ID,
        "time.min": start,
        "time.max": end,
        "parameters": ",".join(REQUESTED_PARAMETERS),
        "format": "json",
    }
    response = requests.get(f"{base_url.rstrip('/')}/data", params=params, timeout=60)
    _raise_for_hapi_status(response)
    payload = response.json()

    names = [parameter["name"] for parameter in payload["parameters"]]
    fills = {parameter["name"]: parameter.get("fill") for parameter in payload["parameters"]}
    return [
        GoesProtonFlux.from_api_row(dict(zip(names, row)), fills)
        for row in payload.get("data", [])
    ]


def upsert_goes_integral_protons(conn, records: list[GoesProtonFlux]) -> int:
    if not records:
        return 0

    with conn.cursor() as cur:
        cur.executemany(
            """
            INSERT INTO goes_integral_protons (
                time, proton_satellite,
                p1_pfu, p5_pfu, p10_pfu, p30_pfu,
                p50_pfu, p60_pfu, p100_pfu, p500_pfu
            )
            VALUES (
                %(time)s, %(proton_satellite)s,
                %(p1_pfu)s, %(p5_pfu)s, %(p10_pfu)s, %(p30_pfu)s,
                %(p50_pfu)s, %(p60_pfu)s, %(p100_pfu)s, %(p500_pfu)s
            )
            ON CONFLICT (time) DO UPDATE SET
                proton_satellite = EXCLUDED.proton_satellite,
                p1_pfu = EXCLUDED.p1_pfu,
                p5_pfu = EXCLUDED.p5_pfu,
                p10_pfu = EXCLUDED.p10_pfu,
                p30_pfu = EXCLUDED.p30_pfu,
                p50_pfu = EXCLUDED.p50_pfu,
                p60_pfu = EXCLUDED.p60_pfu,
                p100_pfu = EXCLUDED.p100_pfu,
                p500_pfu = EXCLUDED.p500_pfu,
                ingested_at = now()
            """,
            [record.__dict__ for record in records],
        )
    conn.commit()
    return len(records)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--start", default=os.environ.get("GOES_PROTONS_START", DEFAULT_START))
    parser.add_argument("--end", default=os.environ.get("GOES_PROTONS_END", DEFAULT_END))
    args = parser.parse_args()

    records = fetch_goes_integral_protons(start=args.start, end=args.end)

    conn = get_connection()
    try:
        ensure_goes_integral_protons_table(conn)
        count = upsert_goes_integral_protons(conn, records)
    finally:
        conn.close()

    print(f"Upserted {count} GOES integral proton records ({args.start} .. {args.end}).")


if __name__ == "__main__":
    main()
