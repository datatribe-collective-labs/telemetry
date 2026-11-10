def test_loop_end_met_s_is_the_end_of_the_oem_arc(make_runner, oem_end_met_s):
    assert make_runner(loop=True)._loop_end_met_s() == oem_end_met_s


def test_loop_end_met_s_is_none_when_loop_is_off(make_runner):
    assert make_runner(loop=False)._loop_end_met_s() is None


def test_loop_end_met_s_is_none_without_oem_arc(make_runner, capsys):
    assert make_runner(loop=True, oem=False)._loop_end_met_s() is None
    assert "not looping" in capsys.readouterr().out


def test_loop_end_met_s_is_none_when_start_is_past_the_arc(make_runner, oem_end_met_s, capsys):
    assert make_runner(loop=True, start_met_seconds=oem_end_met_s + 1)._loop_end_met_s() is None
    assert "not looping" in capsys.readouterr().out
