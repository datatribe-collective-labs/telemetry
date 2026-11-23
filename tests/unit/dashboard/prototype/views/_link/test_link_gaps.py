import pandas as pd

from dashboard.src.prototype.views._link import UNKNOWN_REASON, link_gaps


def test_link_gaps_finds_each_gap_with_its_reason(comms, at):
    df = comms((0, 9, "NOMINAL", "NONE"), (10, 14, "NO_LINK", "OUT_OF_DSN_VIEW"), (15, 19, "NOMINAL", "NONE"),
               (20, 24, "NO_LINK", "MOON_BLOCKED"), (25, 29, "NOMINAL", "NONE"))
    gaps = link_gaps(df)
    assert [(g.reason, g.start, g.end) for g in gaps] == [
        ("OUT_OF_DSN_VIEW", at(10), at(15)),
        ("MOON_BLOCKED", at(20), at(25)),
    ]


def test_link_gaps_splits_back_to_back_reasons(comms, at):
    df = comms((0, 4, "NO_LINK", "OUT_OF_DSN_VIEW"), (5, 9, "NO_LINK", "MOON_BLOCKED"), (10, 12, "NOMINAL", "NONE"))
    gaps = link_gaps(df)
    assert [(g.reason, g.start, g.end) for g in gaps] == [
        ("OUT_OF_DSN_VIEW", at(0), at(5)),
        ("MOON_BLOCKED", at(5), at(10)),
    ]


def test_link_gaps_keeps_a_gap_still_open_at_the_end(comms, at):
    gaps = link_gaps(comms((0, 4, "NOMINAL", "NONE"), (5, 9, "NO_LINK", "MOON_BLOCKED")))
    assert (gaps[0].start, gaps[0].end) == (at(5), at(9))


def test_link_gaps_labels_a_missing_reason_as_unknown(comms):
    gaps = link_gaps(comms((0, 4, "NOMINAL", "NONE"), (5, 9, "NO_LINK", None), (10, 12, "NOMINAL", "NONE")))
    assert [g.reason for g in gaps] == [UNKNOWN_REASON]
    assert gaps[0].label == "No link"


def test_link_gaps_ignores_a_weak_signal(comms):
    assert link_gaps(comms((0, 9, "DEGRADED", "NONE"))) == []


def test_link_gaps_empty_is_empty():
    assert link_gaps(pd.DataFrame()) == []
