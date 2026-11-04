from dashboard.src.prototype.pages._phases import milestones


def test_milestones_lists_burns_separation_and_splashdown_in_time_order(events):
    marks = milestones(events)

    labels = [label for _, label in marks]
    assert [t for t, _ in marks] == sorted(t for t, _ in marks)
    assert len(marks) == 7  # PRB, TLI, 2x OTC, RTC, SEP, RECOVERY - not PRELAUNCH/OBSV
    assert labels[1].startswith("Trans-lunar injection") and "Orion TLI 01/01:37" in labels[1]
    assert labels[-1].startswith("Splashdown")
