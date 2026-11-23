from dashboard.src.prototype.views._blackout import cut_blackout


def test_cut_blackout_splits_a_span_across_it(hour):
    assert cut_blackout([(hour(20), hour(23, 59))]) == [(hour(20), hour(22, 44)), (hour(23, 25), hour(23, 59))]


def test_cut_blackout_keeps_a_span_outside_it(hour):
    span = (hour(10), hour(12))
    assert cut_blackout([span]) == [span]


def test_cut_blackout_trims_a_span_ending_inside_it(hour):
    assert cut_blackout([(hour(22), hour(23))]) == [(hour(22), hour(22, 44))]


def test_cut_blackout_trims_a_span_starting_inside_it(hour):
    assert cut_blackout([(hour(23), hour(23, 50))]) == [(hour(23, 25), hour(23, 50))]


def test_cut_blackout_removes_a_span_fully_inside_it(hour):
    assert cut_blackout([(hour(22, 50), hour(23, 10))]) == []


def test_cut_blackout_keeps_a_span_touching_its_edge(hour):
    span = (hour(22), hour(22, 44))
    assert cut_blackout([span]) == [span]
