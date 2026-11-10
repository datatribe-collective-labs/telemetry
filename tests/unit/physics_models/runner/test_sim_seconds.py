import pytest


def _run(runner, ticks: int) -> list[float]:
    """Sim clock for `ticks` consecutive ticks, advancing the tick counter like run()."""
    clock = []
    for _ in range(ticks):
        clock.append(runner._sim_seconds())
        runner._tick_count += 1
    return clock


def test_sim_seconds_replays_from_start_at_time_scale(make_runner):
    runner = make_runner(start_met_seconds=100.0, time_scale=60.0)

    assert _run(runner, 3) == [100.0, 160.0, 220.0]


def test_sim_seconds_wraps_to_start_after_oem_end_with_loop(make_runner):
    # OEM arc ends at MET 1000 s: ticks 100, 400, 700, 1000, then past the end -> 100
    runner = make_runner(start_met_seconds=100.0, time_scale=300.0, loop=True)

    assert _run(runner, 6) == [100.0, 400.0, 700.0, 1000.0, 100.0, 400.0]


def test_sim_seconds_keeps_the_same_tick_grid_on_every_loop(make_runner):
    # Same timestamps each loop, so the consumer's upsert overwrites instead of adding rows
    runner = make_runner(start_met_seconds=100.0, time_scale=300.0, loop=True)

    clock = _run(runner, 12)

    assert clock[0:4] == clock[4:8] == clock[8:12]


def test_sim_seconds_runs_past_oem_end_without_loop(make_runner):
    runner = make_runner(start_met_seconds=100.0, time_scale=300.0)

    assert _run(runner, 6)[-1] == pytest.approx(1600.0)


def test_sim_seconds_resets_the_models_when_it_loops(make_runner):
    runner = make_runner(start_met_seconds=100.0, time_scale=300.0, loop=True)
    first_models = (runner.thermal_model, runner.power_model, runner.cross_model)
    runner.power_model.battery_soc = 0.5

    _run(runner, 5)  # the 5th tick loops

    assert runner.thermal_model is not first_models[0]
    assert runner.cross_model is not first_models[2]
    assert runner.power_model.battery_soc == 1.0
