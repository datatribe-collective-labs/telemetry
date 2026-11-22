"""Tests for SimulatorRunner._run_tick (validate, then publish all or nothing)."""

SENDS = (
    "send_state", "send_thermal", "send_power", "send_comms", "send_radiation",
    "send_cross_model", "send_packet", "send_ml_features",
)


def _break_thermal(runner):
    real_tick = runner._tick_thermal

    def bad_tick(current_tick, met):
        return real_tick(current_tick, met).model_copy(update={"temp_sun_face_k": float("nan")})

    runner._tick_thermal = bad_tick


def test_run_tick_publishes_every_output_of_a_valid_tick(make_runner):
    runner = make_runner(oem=False)

    assert runner._run_tick() is True

    for name in SENDS:
        getattr(runner.producer, name).assert_called_once()
    assert runner._tick_count == 1


def test_run_tick_packet_carries_link_context(make_runner):
    runner = make_runner(oem=False)

    runner._run_tick()

    packet = runner.producer.send_packet.call_args.args[0]
    comms = runner.producer.send_comms.call_args.args[0]
    assert packet.link_loss_reason == comms.link_loss_reason
    assert packet.dsn_visibility == runner._last_state.dsn_visibility


def test_run_tick_invalid_tick_publishes_nothing(make_runner, capsys):
    runner = make_runner(oem=False)
    _break_thermal(runner)

    assert runner._run_tick() is False

    for name in SENDS:
        getattr(runner.producer, name).assert_not_called()
    assert "thermal.temp_sun_face_k is not finite" in capsys.readouterr().out


def test_run_tick_invalid_tick_does_not_reach_the_bus(make_runner):
    runner = make_runner(oem=False)
    runner._run_tick()
    last_valid = runner.cross_model.electronics_bay_temp_k, runner.cross_model.power_state
    _break_thermal(runner)

    runner._run_tick()

    assert (runner.cross_model.electronics_bay_temp_k, runner.cross_model.power_state) == last_valid


def test_run_tick_invalid_tick_still_advances_the_clock(make_runner):
    runner = make_runner(oem=False)
    _break_thermal(runner)

    runner._run_tick()

    assert runner._tick_count == 1


def test_run_tick_publishes_again_after_an_invalid_tick(make_runner):
    runner = make_runner(oem=False)
    healthy_tick = runner._tick_thermal
    _break_thermal(runner)
    assert runner._run_tick() is False

    runner._tick_thermal = healthy_tick

    assert runner._run_tick() is True
    runner.producer.send_packet.assert_called_once()
