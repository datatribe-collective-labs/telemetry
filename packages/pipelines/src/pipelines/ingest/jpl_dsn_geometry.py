"""Ingest Artemis II Orion (-1024) look angles from each DSN complex into `dsn_site_geometry`.

Source: https://ssd.jpl.nasa.gov/api/horizons.api (OBSERVER ephemeris, one
topocentric query per Deep Space Network site).
Fair-use policy: one request at a time, no guaranteed availability - this
module requests the sites sequentially, never concurrently.

Each row is where Orion sat in one DSN antenna's sky at one epoch: azimuth,
elevation, range, range-rate and one-way light time. `visible` applies the
10 degree elevation cutoff that the `dsn_visibility` field in
`contracts/src/odcs/01_state_engine.odcs.yaml` is defined against.

Run directly: `uv run --package pipelines python -m pipelines.ingest.jpl_dsn_geometry`
"""

import argparse
import csv
import io
import os
from dataclasses import dataclass
from datetime import UTC, datetime

import psycopg
import requests

from pipelines.db import get_connection

DEFAULT_BASE_URL = "https://ssd.jpl.nasa.gov/api/horizons.api"
DEFAULT_COMMAND = "-1024"
DEFAULT_START_TIME = "2026-04-02 02:00"
DEFAULT_STOP_TIME = "2026-04-10 23:00"
DEFAULT_STEP_SIZE = "1 h"

ELEVATION_CUTOFF_DEG = 10.0
KM_PER_AU = 149597870.7


@dataclass(frozen=True)
class DsnSite:
    site: str
    complex: str
    east_longitude_deg: float
    latitude_deg: float
    altitude_km: float


# Geodetic coordinates of each complex's 70 m antenna (approximate, per the
# DSN Telecommunications Link Design Handbook 810-005, module 301). Precision
# of ~0.001 deg is far below what matters for a spacecraft 10^4-10^5 km away.
DSN_SITES: dict[str, DsnSite] = {
    "DSS-14": DsnSite("DSS-14", "Goldstone", 243.1105, 35.4259, 1.002),
    "DSS-43": DsnSite("DSS-43", "Canberra", 148.9813, -35.4024, 0.689),
    "DSS-63": DsnSite("DSS-63", "Madrid", 355.7520, 40.4313, 0.865),
}

DSN_SITE_GEOMETRY_SCHEMA = """
CREATE TABLE IF NOT EXISTS dsn_site_geometry (
    target_id TEXT NOT NULL DEFAULT '-1024',
    site TEXT NOT NULL,
    complex TEXT NOT NULL,
    epoch TIMESTAMPTZ NOT NULL,
    azimuth_deg DOUBLE PRECISION,
    elevation_deg DOUBLE PRECISION,
    range_km DOUBLE PRECISION,
    range_rate_kms DOUBLE PRECISION,
    light_time_s DOUBLE PRECISION,
    visible BOOLEAN,
    ingested_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    PRIMARY KEY (target_id, site, epoch)
);
"""

DSN_SITE_GEOMETRY_HYPERTABLE = """
SELECT create_hypertable('dsn_site_geometry', 'epoch', if_not_exists => TRUE);
"""


def ensure_dsn_site_geometry_table(conn: psycopg.Connection) -> None:
    with conn.cursor() as cur:
        cur.execute(DSN_SITE_GEOMETRY_SCHEMA)
        cur.execute("SELECT 1 FROM pg_extension WHERE extname = 'timescaledb'")
        if cur.fetchone():
            cur.execute(DSN_SITE_GEOMETRY_HYPERTABLE)
        else:
            print(
                "timescaledb extension not installed - using a regular Postgres table."
            )
    conn.commit()


@dataclass
class DsnSiteGeometry:
    target_id: str
    site: str
    complex: str
    epoch: datetime
    azimuth_deg: float | None
    elevation_deg: float | None
    range_km: float | None
    range_rate_kms: float | None
    light_time_s: float | None
    visible: bool | None


def _to_float(val: str | None) -> float | None:
    """Horizons prints `n.a.` (or leaves blank) where a quantity is unavailable."""
    if val is None:
        return None
    try:
        return float(val)
    except ValueError:
        return None


def _parse_horizons_date(date_str: str) -> datetime:
    clean = date_str.replace("A.D.", "").replace("B.C.", "").strip()
    for fmt in ("%Y-%b-%d %H:%M:%S.%f", "%Y-%b-%d %H:%M:%S", "%Y-%b-%d %H:%M"):
        try:
            return datetime.strptime(clean, fmt).replace(tzinfo=UTC)
        except ValueError:
            pass
    return datetime.fromisoformat(clean).replace(tzinfo=UTC)


def is_visible(elevation_deg: float | None) -> bool | None:
    if elevation_deg is None:
        return None
    return elevation_deg >= ELEVATION_CUTOFF_DEG


def parse_observer_table(
    result_text: str, target_id: str, site: DsnSite
) -> list[DsnSiteGeometry]:
    """Parse the CSV block of a Horizons OBSERVER result (QUANTITIES='4,20,21').

    Columns are matched by header name, not position, because Horizons inserts
    unnamed solar/lunar-presence flag columns after the date. Horizons reports
    range (`delta`) in AU and light time in minutes; both are converted here.
    """
    if "$$SOE" not in result_text or "$$EOE" not in result_text:
        print(f"No ephemeris data markers ($$SOE / $$EOE) found for {site.site}.")
        return []

    preamble, rest = result_text.split("$$SOE", 1)
    body = rest.split("$$EOE", 1)[0].strip()
    header_line = next(
        line for line in reversed(preamble.splitlines()) if "Date__(UT)" in line
    )
    header = [col.strip() for col in next(csv.reader([header_line]))]

    def _col(prefix: str) -> int:
        for i, name in enumerate(header):
            if name.startswith(prefix):
                return i
        raise ValueError(f"Could not find column {prefix!r} in {header}")

    date_i = _col("Date__(UT)")
    azi_i = _col("Azi")
    elev_i = _col("Elev")
    delta_i = _col("delta")
    deldot_i = _col("deldot")
    lt_i = _col("1-way_down_LT")

    records: list[DsnSiteGeometry] = []
    for row in csv.reader(io.StringIO(body)):
        if not row:
            continue
        row = [cell.strip() for cell in row]
        elevation = _to_float(row[elev_i])
        delta_au = _to_float(row[delta_i])
        lt_min = _to_float(row[lt_i])
        records.append(
            DsnSiteGeometry(
                target_id=target_id,
                site=site.site,
                complex=site.complex,
                epoch=_parse_horizons_date(row[date_i]),
                azimuth_deg=_to_float(row[azi_i]),
                elevation_deg=elevation,
                range_km=delta_au * KM_PER_AU if delta_au is not None else None,
                range_rate_kms=_to_float(row[deldot_i]),
                light_time_s=lt_min * 60.0 if lt_min is not None else None,
                visible=is_visible(elevation),
            )
        )
    return records


def fetch_site_geometry(
    site: DsnSite,
    command: str = DEFAULT_COMMAND,
    start_time: str = DEFAULT_START_TIME,
    stop_time: str = DEFAULT_STOP_TIME,
    step_size: str = DEFAULT_STEP_SIZE,
    base_url: str | None = None,
) -> list[DsnSiteGeometry]:
    base_url = base_url or os.environ.get("JPL_HORIZONS_BASE_URL", DEFAULT_BASE_URL)
    params = {
        "format": "json",
        "COMMAND": f"'{command}'",
        "OBJ_DATA": "NO",
        "MAKE_EPHEM": "YES",
        "EPHEM_TYPE": "OBSERVER",
        "CENTER": "'coord@399'",
        "COORD_TYPE": "GEODETIC",
        "SITE_COORD": (
            f"'{site.east_longitude_deg},{site.latitude_deg},{site.altitude_km}'"
        ),
        "START_TIME": f"'{start_time}'",
        "STOP_TIME": f"'{stop_time}'",
        "STEP_SIZE": f"'{step_size}'",
        # 4 = azimuth/elevation, 20 = range & range-rate, 21 = one-way light time
        "QUANTITIES": "'4,20,21'",
        "ANG_FORMAT": "DEG",
        # Geometric elevation, no refraction: matches the plain 10 deg cutoff.
        "APPARENT": "AIRLESS",
        "CSV_FORMAT": "YES",
    }
    response = requests.get(base_url, params=params, timeout=30)
    response.raise_for_status()
    data = response.json()

    if "error" in data:
        raise RuntimeError(f"JPL Horizons API Error: {data['error']}")

    return parse_observer_table(data.get("result", ""), command.strip("'"), site)


def fetch_dsn_geometry(
    sites: list[DsnSite] | None = None,
    command: str = DEFAULT_COMMAND,
    start_time: str = DEFAULT_START_TIME,
    stop_time: str = DEFAULT_STOP_TIME,
    step_size: str = DEFAULT_STEP_SIZE,
    base_url: str | None = None,
) -> list[DsnSiteGeometry]:
    """Fetch every site one after another (JPL fair use: no concurrent requests)."""
    records: list[DsnSiteGeometry] = []
    for site in sites or list(DSN_SITES.values()):
        records.extend(
            fetch_site_geometry(
                site,
                command=command,
                start_time=start_time,
                stop_time=stop_time,
                step_size=step_size,
                base_url=base_url,
            )
        )
    return records


def upsert_dsn_site_geometry(
    conn: psycopg.Connection, records: list[DsnSiteGeometry]
) -> int:
    if not records:
        return 0

    with conn.cursor() as cur:
        cur.executemany(
            """
            INSERT INTO dsn_site_geometry (
                target_id, site, complex, epoch,
                azimuth_deg, elevation_deg, range_km, range_rate_kms,
                light_time_s, visible
            )
            VALUES (
                %(target_id)s, %(site)s, %(complex)s, %(epoch)s,
                %(azimuth_deg)s, %(elevation_deg)s, %(range_km)s, %(range_rate_kms)s,
                %(light_time_s)s, %(visible)s
            )
            ON CONFLICT (target_id, site, epoch) DO UPDATE SET
                complex = EXCLUDED.complex,
                azimuth_deg = EXCLUDED.azimuth_deg,
                elevation_deg = EXCLUDED.elevation_deg,
                range_km = EXCLUDED.range_km,
                range_rate_kms = EXCLUDED.range_rate_kms,
                light_time_s = EXCLUDED.light_time_s,
                visible = EXCLUDED.visible,
                ingested_at = now()
            """,
            [record.__dict__ for record in records],
        )
    conn.commit()
    return len(records)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--command", default=os.environ.get("HORIZONS_COMMAND", DEFAULT_COMMAND)
    )
    parser.add_argument(
        "--start-time", default=os.environ.get("HORIZONS_START", DEFAULT_START_TIME)
    )
    parser.add_argument(
        "--stop-time", default=os.environ.get("HORIZONS_STOP", DEFAULT_STOP_TIME)
    )
    parser.add_argument(
        "--step-size", default=os.environ.get("HORIZONS_STEP", DEFAULT_STEP_SIZE)
    )
    parser.add_argument(
        "--site",
        action="append",
        choices=sorted(DSN_SITES),
        help="DSN antenna to query (repeatable). Default: all three complexes.",
    )
    args = parser.parse_args()

    sites = [DSN_SITES[s] for s in args.site] if args.site else None
    records = fetch_dsn_geometry(
        sites=sites,
        command=args.command,
        start_time=args.start_time,
        stop_time=args.stop_time,
        step_size=args.step_size,
    )

    conn = get_connection()
    try:
        ensure_dsn_site_geometry_table(conn)
        count = upsert_dsn_site_geometry(conn, records)
    finally:
        conn.close()

    print(
        f"Upserted {count} DSN site geometry records "
        f"({args.start_time} .. {args.stop_time})."
    )


if __name__ == "__main__":
    main()
