"""Moon position over the Artemis II mission, from a bundled JPL Horizons table.

`moon_ephemeris.csv` records its exact Horizons query in its header. With its 10-minute
step, linear interpolation is off by at most about 0.12 km.
"""

import csv
from datetime import UTC, datetime
from functools import lru_cache
from pathlib import Path

import numpy as np

MOON_RADIUS_KM = 1737.4
EPHEMERIS_FILE = Path(__file__).with_name("moon_ephemeris.csv")


@lru_cache(maxsize=1)
def _load_ephemeris() -> tuple[np.ndarray, np.ndarray]:
    """(epochs as Unix seconds, Nx3 positions in km), read once."""
    with EPHEMERIS_FILE.open(encoding="utf-8", newline="") as handle:
        rows = list(csv.DictReader(line for line in handle if not line.startswith("#")))
    epochs = [datetime.fromisoformat(row["epoch_utc"]).timestamp() for row in rows]
    positions = [[float(row["x_km"]), float(row["y_km"]), float(row["z_km"])] for row in rows]
    return np.array(epochs), np.array(positions)


def compute_moon_position_km(t: datetime) -> np.ndarray:
    """Earth-centred EME2000 Moon position at time t (km).

    A naive time is read as UTC. Times outside the table use its nearest end, as the
    OEM reader does.
    """
    aware = t if t.tzinfo else t.replace(tzinfo=UTC)
    epochs, positions = _load_ephemeris()
    return np.array([np.interp(aware.timestamp(), epochs, positions[:, axis]) for axis in range(3)])
