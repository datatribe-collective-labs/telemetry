import pandas as pd
import pytest

T0 = pd.Timestamp("2026-04-06 22:00", tz="UTC")


@pytest.fixture
def at():
    """The time `minute` minutes after the fixtures' start."""
    return lambda minute: T0 + pd.Timedelta(minutes=minute)


@pytest.fixture
def comms(at):
    """One row a minute from (first minute, last minute, state, reason) stretches."""

    def build(*stretches):
        rows = [
            {"timestamp_utc": at(m), "comm_state": state, "link_loss_reason": reason}
            for first, last, state, reason in stretches
            for m in range(first, last + 1)
        ]
        return pd.DataFrame(rows)

    return build
