"""Fixtures for unit tests of dashboard.src.prototype.pages._phases."""

import pandas as pd
import pytest

H = 3600.0
D = 86_400.0


@pytest.fixture
def events():
    """A cut-down planned timeline: the segments the phase logic keys on, plus filler."""
    rows = [
        (0, 1 * H, "PRELAUNCH", "Prelaunch to Ascent"),
        (13.75 * H, 14 * H, "BURN_PRB", "Orion PRB 0/13:45"),
        (D + 1.6 * H, D + 2 * H, "BURN_TLI", "Orion TLI 01/01:37"),
        (2 * D, 2 * D + 0.5 * H, "BURN_OTC", "OTC-1 02/00:07"),
        (4 * D + 5.4 * H, 4 * D + 6 * H, "BURN_OTC", "OTC-3 04/05:23"),
        (5 * D, 5 * D + 3 * H, "OBSV", "Lunar observation"),
        (6 * D + 4.4 * H, 6 * D + 5 * H, "BURN_RTC", "RTC-1 06/04:23"),
        (9 * D + 1.2 * H, 9 * D + 1.5 * H, "SEP", "CM/SM Sep 09/01:13"),
        (9 * D + 1.5 * H, 9 * D + 2 * H, "RECOVERY", "Splashdown / Recovery"),
    ]
    df = pd.DataFrame(rows, columns=["met_start_s", "met_end_s", "mode", "description"])
    return df.sample(frac=1, random_state=0)  # the logic must not rely on input order
