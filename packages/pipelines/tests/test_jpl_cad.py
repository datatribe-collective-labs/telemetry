"""Tests for pipelines.ingest.jpl_cad.

Pure-logic and HTTP-mocked tests below need no Docker and always run.
Tests marked `@pytest.mark.integration` need the `timescaledb_test` Docker
service (see conftest.py) - they're skipped automatically if it's not up.
"""

from datetime import datetime, timezone
from unittest.mock import MagicMock

import pytest
import requests
import responses
from responses import matchers

from pipelines.ingest.jpl_cad import (
    CLOSE_APPROACHES_HYPERTABLE,
    CLOSE_APPROACHES_SCHEMA,
    DEFAULT_BASE_URL,
    CloseApproach,
    _parse_calendar_date,
    _to_float,
    ensure_close_approaches_table,
    fetch_close_approaches,
    upsert_close_approaches,
)

# A small, realistic sample of what the CAD API actually returns: a list of
# field names plus parallel rows of string values. The second row omits every
# optional field (as blank strings) to exercise the None/default-fallback
# paths in CloseApproach.from_api_record.
CAD_FIELDS = [
    "des", "orbit_id", "jd", "cd",
    "dist", "dist_min", "dist_max", "v_rel", "v_inf", "h", "body",
]
CAD_ROWS = [
    ["2024 AB", "5", "2460500.5", "2029-Apr-13 21:46",
     "0.0421", "0.0400", "0.0450", "12.3", "11.9", "22.1", "Earth"],
    ["2025 XY", "12", "2460510.75", "2029-May-02 03:10",
     "0.0399", "", "", "9.87", "", "", ""],
]


def make_close_approach(**overrides) -> CloseApproach:
    defaults = dict(
        des="2024 AB",
        orbit_id="5",
        close_approach_jd=2460500.5,
        close_approach_time=datetime(2029, 4, 13, 21, 46, tzinfo=timezone.utc),
        dist_au=0.0421,
        dist_min_au=0.0400,
        dist_max_au=0.0450,
        v_rel_kms=12.3,
        v_inf_kms=11.9,
        h_mag=22.1,
        body="Earth",
    )
    defaults.update(overrides)
    return CloseApproach(**defaults)


# --- _to_float -----------------------------------------------------------

def test_to_float_parses_valid_string():
    assert _to_float("0.0421") == 0.0421


@pytest.mark.parametrize("value", [None, ""])
def test_to_float_handles_none_and_empty(value):
    assert _to_float(value) is None


# --- _parse_calendar_date --------------------------------------------------

def test_parse_calendar_date():
    assert _parse_calendar_date("2029-Apr-13 21:46") == datetime(
        2029, 4, 13, 21, 46, tzinfo=timezone.utc
    )


# --- CloseApproach.from_api_record -----------------------------------------

def test_from_api_record_maps_all_fields():
    record = dict(zip(CAD_FIELDS, CAD_ROWS[0]))

    result = CloseApproach.from_api_record(record, default_body="Earth")

    assert result == make_close_approach()


def test_from_api_record_missing_optional_fields_are_none():
    record = dict(zip(CAD_FIELDS, CAD_ROWS[1]))

    result = CloseApproach.from_api_record(record, default_body="Earth")

    assert result.dist_min_au is None
    assert result.dist_max_au is None
    assert result.v_inf_kms is None
    assert result.h_mag is None


def test_from_api_record_defaults_body_when_blank():
    record = dict(zip(CAD_FIELDS, CAD_ROWS[1]))

    result = CloseApproach.from_api_record(record, default_body="Earth")

    assert result.body == "Earth"


# --- fetch_close_approaches (HTTP mocked, no Docker) -----------------------

@responses.activate
def test_fetch_close_approaches_parses_response():
    responses.add(
        responses.GET,
        DEFAULT_BASE_URL,
        json={"fields": CAD_FIELDS, "data": CAD_ROWS},
        match=[
            matchers.query_param_matcher(
                {"date-min": "now", "date-max": "+60", "dist-max": "0.05", "body": "Earth"}
            )
        ],
    )

    result = fetch_close_approaches()

    assert result == [
        make_close_approach(),
        make_close_approach(
            des="2025 XY", orbit_id="12", close_approach_jd=2460510.75,
            close_approach_time=datetime(2029, 5, 2, 3, 10, tzinfo=timezone.utc),
            dist_au=0.0399, dist_min_au=None, dist_max_au=None,
            v_rel_kms=9.87, v_inf_kms=None, h_mag=None, body="Earth",
        ),
    ]


@responses.activate
def test_fetch_close_approaches_empty_data_returns_empty_list():
    responses.add(responses.GET, DEFAULT_BASE_URL, json={"fields": CAD_FIELDS, "data": []})

    assert fetch_close_approaches() == []


@responses.activate
def test_fetch_close_approaches_raises_for_http_error():
    responses.add(responses.GET, DEFAULT_BASE_URL, status=500)

    with pytest.raises(requests.HTTPError):
        fetch_close_approaches()


# --- upsert_close_approaches: pure short-circuit (no DB) -------------------

def test_upsert_empty_list_returns_zero_without_touching_db():
    assert upsert_close_approaches(conn=None, records=[]) == 0


# --- ensure_close_approaches_table: hypertable branch (mocked, no Docker) --

def test_ensure_table_skips_hypertable_when_extension_missing():
    """timescaledb isn't installed -> falls back to a plain table, no crash."""
    cursor = MagicMock()
    cursor.fetchone.return_value = None
    conn = MagicMock()
    conn.cursor.return_value.__enter__.return_value = cursor

    ensure_close_approaches_table(conn)

    executed_sql = [call.args[0] for call in cursor.execute.call_args_list]
    assert CLOSE_APPROACHES_SCHEMA in executed_sql
    assert CLOSE_APPROACHES_HYPERTABLE not in executed_sql
    conn.commit.assert_called_once()


# --- Integration tests: real timescaledb_test database --------------------

@pytest.mark.integration
def test_ensure_close_approaches_table_creates_table(db_connection):
    with db_connection.cursor() as cur:
        cur.execute("DROP TABLE IF EXISTS close_approaches")
    db_connection.commit()

    ensure_close_approaches_table(db_connection)

    with db_connection.cursor() as cur:
        cur.execute(
            "SELECT 1 FROM information_schema.tables WHERE table_name = 'close_approaches'"
        )
        assert cur.fetchone() is not None


@pytest.mark.integration
def test_upsert_inserts_new_records(clean_close_approaches_table):
    conn = clean_close_approaches_table
    records = [
        make_close_approach(des="2024 AB"),
        make_close_approach(des="2025 XY", orbit_id="12"),
    ]

    count = upsert_close_approaches(conn, records)

    assert count == 2
    with conn.cursor() as cur:
        cur.execute("SELECT count(*) FROM close_approaches")
        assert cur.fetchone()[0] == 2


@pytest.mark.integration
def test_upsert_updates_existing_record_on_conflict(clean_close_approaches_table):
    conn = clean_close_approaches_table
    upsert_close_approaches(conn, [make_close_approach(dist_au=0.0421)])

    upsert_close_approaches(conn, [make_close_approach(dist_au=0.0999)])

    with conn.cursor() as cur:
        cur.execute("SELECT count(*), max(dist_au) FROM close_approaches")
        row_count, dist_au = cur.fetchone()
        assert row_count == 1
        assert dist_au == 0.0999
