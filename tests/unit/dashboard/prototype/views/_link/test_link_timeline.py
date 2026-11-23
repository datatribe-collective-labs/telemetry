from dashboard.src.prototype.views._link import LinkGap, link_timeline


def test_link_timeline_has_one_trace_per_reason_after_connected(at):
    gaps = [LinkGap("OUT_OF_DSN_VIEW", at(5), at(9)), LinkGap("MOON_BLOCKED", at(12), at(20)),
            LinkGap("OUT_OF_DSN_VIEW", at(25), at(30))]
    fig = link_timeline(gaps, at(0), at(40))
    assert [t.name for t in fig.data] == ["Connected", "Out of DSN view", "Behind the Moon"]
    assert len(fig.data[1].x) == 2


def test_link_timeline_hover_gives_reason_times_and_length(at):
    fig = link_timeline([LinkGap("MOON_BLOCKED", at(43), at(84))], at(0), at(100))
    text = fig.data[1].hovertext[0]
    assert "Behind the Moon" in text
    assert "Apr 06 22:43" in text
    assert "41 min" in text


def test_link_timeline_marks_now_only_when_given(at):
    assert len(link_timeline([], at(0), at(10)).layout.shapes) == 0
    assert len(link_timeline([], at(0), at(10), now=at(5)).layout.shapes) == 1
