"""Ingest the Artemis II planned attitude/mission timeline into `mission_events`.

Source: `contracts.planned_attitude` — the truth model extracted
from the NASA "Artemis II Overview Timeline - FINAL" PDF (graphical document; the
code module is the debuggable, versioned form).

⚠️ DRAFT DATA: the extracted timeline has not yet been fact-checked against the
PDF. Consumers must treat `mission_events` as unvalidated until that review is
done (tracked in docs/guides/TIMELINE_FACTCHECK_CHECKLIST.md).

Each row is one contiguous attitude segment keyed by Mission Elapsed Time.
The dashboard v1 timeline strip and mission-phase logic read this table.

Run directly: `uv run --package pipelines python -m pipelines.ingest.mission_events`
"""

import argparse
from dataclasses import dataclass

import psycopg
from contracts.planned_attitude import ATTITUDE_TIMELINE

from pipelines.db import get_connection

MISSION_EVENTS_SCHEMA = """
CREATE TABLE IF NOT EXISTS mission_events (
    met_start_s DOUBLE PRECISION NOT NULL,
    met_end_s DOUBLE PRECISION NOT NULL,
    mode TEXT NOT NULL,
    description TEXT NOT NULL,
    ingested_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    PRIMARY KEY (met_start_s)
);
"""


@dataclass(frozen=True)
class MissionEventRow:
    met_start_s: float
    met_end_s: float
    mode: str
    description: str

    @property
    def met_start_hms(self) -> str:
        """Display helper: 'D/HH:MM' Mission Elapsed Time string."""
        s = int(self.met_start_s)
        d, rem = divmod(s, 86400)
        h, rem = divmod(rem, 3600)
        return f"{d}/{h:02d}:{rem // 60:02d}"


def timeline_to_rows() -> list[MissionEventRow]:
    """Convert the in-code attitude timeline to mission event rows."""
    return [
        MissionEventRow(
            met_start_s=seg.met_start.total_seconds(),
            met_end_s=seg.met_end.total_seconds(),
            mode=seg.mode.value,
            description=seg.description,
        )
        for seg in ATTITUDE_TIMELINE
    ]


def ensure_mission_events_table(conn: psycopg.Connection) -> None:
    with conn.cursor() as cur:
        cur.execute(MISSION_EVENTS_SCHEMA)
    conn.commit()


def replace_mission_events(conn: psycopg.Connection, rows: list[MissionEventRow]) -> int:
    """Full replace: the timeline is a small curated truth model (107 rows)."""
    with conn.cursor() as cur:
        cur.execute("TRUNCATE mission_events")
        cur.executemany(
            "INSERT INTO mission_events (met_start_s, met_end_s, mode, description) "
            "VALUES (%(met_start_s)s, %(met_end_s)s, %(mode)s, %(description)s)",
            [r.__dict__ for r in rows],
        )
    conn.commit()
    return len(rows)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.parse_args()
    rows = timeline_to_rows()
    with get_connection() as conn:
        ensure_mission_events_table(conn)
        n = replace_mission_events(conn, rows)
    print(f"Done. {n} mission events ingested.")


if __name__ == "__main__":
    main()
