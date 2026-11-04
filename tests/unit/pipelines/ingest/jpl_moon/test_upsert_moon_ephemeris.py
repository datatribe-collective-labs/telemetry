"""Unit tests for pipelines.ingest.jpl_moon.upsert_moon_ephemeris (connection mocked)."""

from datetime import UTC, datetime
from unittest.mock import MagicMock

from pipelines.ingest.jpl_moon import MoonRecord, upsert_moon_ephemeris


def _record() -> MoonRecord:
    return MoonRecord(
        epoch=datetime(2026, 4, 2, tzinfo=UTC), jd=2461132.5, x_km=1.0, y_km=2.0, z_km=3.0,
        vx_kms=0.1, vy_kms=0.2, vz_kms=0.3, range_km=3.7,
    )


def test_upsert_moon_ephemeris_writes_rows_keyed_on_epoch():
    conn = MagicMock()
    cur = conn.cursor.return_value.__enter__.return_value

    assert upsert_moon_ephemeris(conn, [_record()]) == 1

    sql, rows = cur.executemany.call_args.args
    assert "ON CONFLICT (epoch)" in sql
    assert rows[0]["x_km"] == 1.0
    conn.commit.assert_called_once()


def test_upsert_moon_ephemeris_skips_empty_input():
    conn = MagicMock()

    assert upsert_moon_ephemeris(conn, []) == 0

    conn.cursor.assert_not_called()
