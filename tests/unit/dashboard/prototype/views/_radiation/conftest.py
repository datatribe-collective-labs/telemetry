import pandas as pd
import pytest

T0 = pd.Timestamp("2026-04-02 02:00", tz="UTC")


@pytest.fixture
def at():
    return lambda minute: T0 + pd.Timedelta(minutes=minute)


@pytest.fixture
def journey(at):
    """One row a minute from (zone, minutes, krad added per minute) stretches."""

    def build(*stretches):
        rows, dose, belt, minute = [], 0.0, 0.0, 0
        for zone, minutes, step in stretches:
            for _ in range(minutes):
                dose += step
                if zone != "DEEP_SPACE":
                    belt += step
                rows.append({"timestamp_utc": at(minute), "radiation_zone": zone, "cumulative_dose_krad": dose,
                             "cumulative_belt_dose_krad": belt, "total_dose_rate_rad_s": step / 60 * 1000})
                minute += 1
        return pd.DataFrame(rows)

    return build
