"""Unit tests for pipelines.ingest.iswa_goes_protons.upsert_goes_integral_protons.

The connection is mocked - no database.
"""

from datetime import UTC, datetime

from pipelines.ingest.iswa_goes_protons import upsert_goes_integral_protons


def test_upsert_goes_integral_protons_returns_zero_for_empty_list_without_db():
    assert upsert_goes_integral_protons(conn=None, records=[]) == 0


def test_upsert_goes_integral_protons_writes_all_records_and_commits(
    mock_connection, make_goes_proton_flux
):
    records = [
        make_goes_proton_flux(),
        make_goes_proton_flux(time=datetime(2026, 4, 1, 22, 5, tzinfo=UTC), p10_pfu=None),
    ]

    count = upsert_goes_integral_protons(mock_connection, records)

    assert count == 2
    sql, params = mock_connection.mock_cursor.executemany.call_args.args
    assert "ON CONFLICT (time) DO UPDATE" in sql
    assert [p["time"] for p in params] == [r.time for r in records]
    assert params[1]["p10_pfu"] is None
    mock_connection.commit.assert_called_once()
