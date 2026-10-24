"""Unit tests for pipelines.ingest.mission_events (no DB)."""

from contracts.planned_attitude import ATTITUDE_TIMELINE
from pipelines.ingest.mission_events import MissionEventRow, timeline_to_rows


def test_timeline_to_rows_matches_source_length():
    assert len(timeline_to_rows()) == len(ATTITUDE_TIMELINE)


def test_rows_are_chronological_and_well_formed():
    rows = timeline_to_rows()
    starts = [r.met_start_s for r in rows]
    assert starts == sorted(starts)
    assert all(r.met_end_s > r.met_start_s for r in rows)
    assert all(r.mode and r.description for r in rows)


def test_key_events_present():
    modes = {r.mode for r in timeline_to_rows()}
    assert "BURN_TLI" in modes
    assert "EDL" in modes
    assert "RECOVERY" in modes


def test_met_display_helper():
    row = MissionEventRow(met_start_s=3600.0 * 25.7, met_end_s=3600.0 * 26, mode="X", description="d")
    assert row.met_start_hms.startswith("1/01")
