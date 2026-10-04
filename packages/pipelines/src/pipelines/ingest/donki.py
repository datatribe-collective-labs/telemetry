"""Ingest NASA CCMC DONKI space-weather events into ``donki_events``.

Source: https://ccmc.gsfc.nasa.gov/DONKI-API/get/

The complete DONKI response object is retained in ``payload`` so that event-
specific schemas are not prematurely normalized. Common timestamps and IDs
are extracted only for indexing, filtering, and provenance.

Run directly, for example:
    uv run --package pipelines python -m pipelines.ingest.donki \
        --start-date 2026-04-01 --end-date 2026-04-10
"""

import argparse
import hashlib
import json
import os
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any

import psycopg
import requests

from pipelines.db import get_connection

DEFAULT_BASE_URL = "https://ccmc.gsfc.nasa.gov/DONKI-API/get"
DEFAULT_START_DATE = "2026-04-01"
DEFAULT_END_DATE = "2026-04-10"
DEFAULT_REQUEST_DELAY_SECONDS = 0.2

EVENT_TYPES = (
    "CME",
    "CMEAnalysis",
    "SEP",
    "FLR",
    "IPS",
    "GST",
    "RBE",
    "HSS",
    "MPC",
    "WSAEnlilSimulations",
)

DONKI_EVENTS_SCHEMA = """
CREATE TABLE IF NOT EXISTS donki_events (
    event_type TEXT NOT NULL,
    event_id TEXT NOT NULL,
    start_time TIMESTAMPTZ,
    end_time TIMESTAMPTZ,
    event_time TIMESTAMPTZ,
    fetched_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    source_url TEXT NOT NULL,
    payload JSONB NOT NULL,
    PRIMARY KEY (event_type, event_id)
);
"""

DONKI_EVENTS_INDEXES = """
CREATE INDEX IF NOT EXISTS idx_donki_events_start_time
    ON donki_events (start_time);
CREATE INDEX IF NOT EXISTS idx_donki_events_event_type_time
    ON donki_events (event_type, event_time);
"""


def ensure_donki_events_table(conn: psycopg.Connection) -> None:
    with conn.cursor() as cur:
        cur.execute(DONKI_EVENTS_SCHEMA)
        cur.execute(DONKI_EVENTS_INDEXES)
        cur.execute("SELECT 1 FROM pg_extension WHERE extname = 'timescaledb'")
        if cur.fetchone():
            # DONKI contains heterogeneous event types and some records do not
            # have a single canonical observation timestamp. Keep this as a
            # regular table until the correlation model has a stable time key.
            pass
    conn.commit()


def _parse_timestamp(value: Any) -> datetime | None:
    if not value or not isinstance(value, str):
        return None
    text = value.strip()
    if not text:
        return None
    if text.endswith("Z"):
        text = text[:-1] + "+00:00"
    try:
        parsed = datetime.fromisoformat(text)
    except ValueError:
        return None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


def _first_timestamp(payload: dict[str, Any], *fields: str) -> datetime | None:
    for field in fields:
        parsed = _parse_timestamp(payload.get(field))
        if parsed is not None:
            return parsed
    return None


def _stable_payload_id(payload: dict[str, Any]) -> str:
    encoded = json.dumps(payload, sort_keys=True, separators=(",", ":"), default=str)
    return "sha256:" + hashlib.sha256(encoded.encode("utf-8")).hexdigest()


def _event_id(event_type: str, payload: dict[str, Any]) -> str:
    id_fields = {
        "CME": ("activityID", "cmeID"),
        "CMEAnalysis": ("activityID", "analysisID", "cmeID", "associatedCMEID"),
        "SEP": ("sepID", "activityID"),
        "FLR": ("flrID", "activityID"),
        "IPS": ("ipsID", "activityID"),
        "GST": ("gstID", "activityID"),
        "RBE": ("rbeID", "activityID"),
        "HSS": ("hssID", "activityID"),
        "MPC": ("mpcID", "activityID"),
        "WSAEnlilSimulations": ("simulationID", "activityID"),
    }
    for field in id_fields.get(event_type, ("activityID",)):
        value = payload.get(field)
        if value not in (None, ""):
            return str(value)
    return _stable_payload_id(payload)


@dataclass(frozen=True)
class DonkiEvent:
    event_type: str
    event_id: str
    start_time: datetime | None
    end_time: datetime | None
    event_time: datetime | None
    source_url: str
    payload: dict[str, Any]

    @classmethod
    def from_api_record(
        cls,
        event_type: str,
        payload: dict[str, Any],
        source_url: str,
    ) -> "DonkiEvent":
        start_time = _first_timestamp(
            payload,
            "startTime",
            "beginTime",
            "eventTime",
            "launchTime",
            "simulationStartTime",
        )
        end_time = _first_timestamp(
            payload,
            "endTime",
            "stopTime",
            "simulationEndTime",
        )
        event_time = _first_timestamp(
            payload,
            "eventTime",
            "peakTime",
            "beginTime",
            "startTime",
            "launchTime",
            "simulationStartTime",
        )
        return cls(
            event_type=event_type,
            event_id=_event_id(event_type, payload),
            start_time=start_time,
            end_time=end_time,
            event_time=event_time,
            source_url=source_url,
            payload=payload,
        )


def fetch_donki_event_type(
    event_type: str,
    start_date: str = DEFAULT_START_DATE,
    end_date: str = DEFAULT_END_DATE,
    base_url: str | None = None,
) -> list[DonkiEvent]:
    if event_type not in EVENT_TYPES:
        raise ValueError(f"Unsupported DONKI event type: {event_type}")

    base_url = base_url or os.environ.get("DONKI_BASE_URL", DEFAULT_BASE_URL)
    endpoint = f"{base_url.rstrip('/')}/{event_type}"
    params = {"startDate": start_date, "endDate": end_date}

    response = requests.get(endpoint, params=params, timeout=30)
    response.raise_for_status()
    payload = response.json()

    if not isinstance(payload, list):
        raise RuntimeError(
            f"Unexpected DONKI response for {event_type}: "
            f"expected a JSON array, got {type(payload).__name__}"
        )

    source_url = response.url
    return [
        DonkiEvent.from_api_record(event_type, item, source_url)
        for item in payload
        if isinstance(item, dict)
    ]


def fetch_donki_events(
    start_date: str = DEFAULT_START_DATE,
    end_date: str = DEFAULT_END_DATE,
    event_types: tuple[str, ...] = EVENT_TYPES,
    base_url: str | None = None,
    request_delay_seconds: float = DEFAULT_REQUEST_DELAY_SECONDS,
) -> list[DonkiEvent]:
    records: list[DonkiEvent] = []
    for index, event_type in enumerate(event_types):
        records.extend(
            fetch_donki_event_type(
                event_type,
                start_date=start_date,
                end_date=end_date,
                base_url=base_url,
            )
        )
        if index < len(event_types) - 1 and request_delay_seconds > 0:
            time.sleep(request_delay_seconds)
    return records


def upsert_donki_events(
    conn: psycopg.Connection,
    records: list[DonkiEvent],
) -> int:
    if not records:
        return 0

    with conn.cursor() as cur:
        cur.executemany(
            """
            INSERT INTO donki_events (
                event_type, event_id, start_time, end_time, event_time,
                source_url, payload
            )
            VALUES (
                %(event_type)s, %(event_id)s, %(start_time)s, %(end_time)s,
                %(event_time)s, %(source_url)s, %(payload)s::jsonb
            )
            ON CONFLICT (event_type, event_id) DO UPDATE SET
                start_time = EXCLUDED.start_time,
                end_time = EXCLUDED.end_time,
                event_time = EXCLUDED.event_time,
                fetched_at = now(),
                source_url = EXCLUDED.source_url,
                payload = EXCLUDED.payload
            """,
            [
                {
                    **record.__dict__,
                    "payload": json.dumps(record.payload, separators=(",", ":")),
                }
                for record in records
            ],
        )
    conn.commit()
    return len(records)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--start-date", default=os.environ.get("DONKI_START_DATE", DEFAULT_START_DATE)
    )
    parser.add_argument(
        "--end-date", default=os.environ.get("DONKI_END_DATE", DEFAULT_END_DATE)
    )
    parser.add_argument(
        "--event-type",
        action="append",
        dest="event_types",
        choices=EVENT_TYPES,
        help="Repeat to select specific DONKI event types; defaults to all supported types.",
    )
    parser.add_argument(
        "--request-delay",
        type=float,
        default=float(os.environ.get("DONKI_REQUEST_DELAY", DEFAULT_REQUEST_DELAY_SECONDS)),
    )
    args = parser.parse_args()

    event_types = tuple(args.event_types) if args.event_types else EVENT_TYPES
    records = fetch_donki_events(
        start_date=args.start_date,
        end_date=args.end_date,
        event_types=event_types,
        request_delay_seconds=args.request_delay,
    )

    conn = get_connection()
    try:
        ensure_donki_events_table(conn)
        count = upsert_donki_events(conn, records)
    finally:
        conn.close()

    print(
        f"Upserted {count} DONKI records "
        f"({args.start_date} .. {args.end_date}; {', '.join(event_types)})."
    )


if __name__ == "__main__":
    main()
