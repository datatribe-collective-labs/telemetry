from dashboard.src.prototype.views._link import LinkGap, gap_at


def test_gap_at_finds_the_gap_in_progress(at):
    gap = LinkGap("MOON_BLOCKED", at(10), at(20))
    assert gap_at([gap], at(15)) == gap


def test_gap_at_is_none_between_gaps(at):
    gaps = [LinkGap("OUT_OF_DSN_VIEW", at(0), at(5)), LinkGap("MOON_BLOCKED", at(10), at(20))]
    assert gap_at(gaps, at(7)) is None


def test_gap_at_prefers_the_later_of_two_touching_gaps(at):
    first = LinkGap("OUT_OF_DSN_VIEW", at(0), at(5))
    second = LinkGap("MOON_BLOCKED", at(5), at(9))
    assert gap_at([first, second], at(5)) == second
