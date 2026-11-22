"""Simulated radiation dose at one cabin sensor (ODCS 03 radiation_model_output).

The output is absorbed dose in water at HERA HSU2, a simplified estimate that is not the
crew's actual dose. It has two sources:

- Radiation belts: two Gaussian shells in geocentric distance, calibrated on the Artemis II
  outbound pass to the Artemis I HSU2 measurements (Nature 634, 48-52, 2024). Targets and
  pass ranges are in issue #19, and `tests/unit/physics_models/radiation/test_calibration.py`
  checks them on the real trajectory.
- Galactic cosmic rays: the measured deep-space rate, reduced by the sky that Earth and the
  Moon block. Geomagnetic shielding near Earth is not modeled.

Dose is computed once on a fixed time grid, so it depends only on the timestamp and not on
replay speed. Cumulative dose counts from the start of the OEM arc.
"""

from dataclasses import dataclass
from datetime import UTC, datetime
from math import ceil
from typing import Literal

import numpy as np

from physics_models.oem import OemEphemeris
from physics_models.state_engine.dsn import WGS84_A_KM
from physics_models.state_engine.moon import (
    MOON_RADIUS_KM,
    compute_moon_position_km,
    compute_moon_positions_km,
)

RadiationZone = Literal["LOW_EARTH", "INNER_BELT", "OUTER_BELT", "DEEP_SPACE"]

EARTH_RADIUS_KM = WGS84_A_KM

# Unit conversions
RAD_PER_MICROGRAY = 1e-4
RAD_PER_KRAD = 1000.0
SECONDS_PER_MINUTE = 60.0
MRAD_HR_PER_RAD_S = 3_600_000.0

# Zone boundaries in Earth radii (ODCS 03 radiation_zone, MODEL_ASSUMPTION)
INNER_BELT_START_RE = 1.2
OUTER_BELT_START_RE = 2.5
DEEP_SPACE_START_RE = 7.0

DOSE_GRID_STEP_S = 10.0
GCR_FREE_SPACE_UGY_MIN = 400.0 / 1440.0  # 0.40 mGy/day, Artemis I HSU2

# NOAA S1 storm threshold, and the highest GOES >=10 MeV flux during the OEM arc.
SEP_THRESHOLD_PFU = 10.0
MISSION_PEAK_PROTON_FLUX_PFU = 6.57


@dataclass(frozen=True)
class BeltShell:
    """A Gaussian dose-rate shell in geocentric distance."""

    peak_ugy_min: float
    center_re: float
    width_re: float


# Peaks: 287 uGy/min is a calibration target; 2.7 uGy/min is read from Fig. 2 of the paper.
# Centres are MODEL_ASSUMPTIONs. Widths are fitted so the outbound pass gives 3.13 mGy
# (inner) and 0.13 mGy (outer).
INNER_BELT = BeltShell(peak_ugy_min=287.0, center_re=1.5, width_re=0.1934)
OUTER_BELT = BeltShell(peak_ugy_min=2.7, center_re=4.0, width_re=0.8699)


@dataclass(frozen=True)
class DoseSample:
    """Dose at one moment, in the units of the radiation contract."""

    belt_rate_rad_s: float
    gcr_rate_rad_s: float
    cumulative_krad: float
    cumulative_belt_krad: float

    @property
    def total_rate_rad_s(self) -> float:
        return self.belt_rate_rad_s + self.gcr_rate_rad_s

    @property
    def rate_mrad_hr(self) -> float:
        return self.total_rate_rad_s * MRAD_HR_PER_RAD_S


def is_sep_event_active() -> bool:
    """True if the mission's GOES proton flux reached the S1 storm threshold."""
    return MISSION_PEAK_PROTON_FLUX_PFU > SEP_THRESHOLD_PFU


def compute_radiation_zone(distance_re: float) -> RadiationZone:
    """Region label from geocentric distance in Earth radii (ODCS 03 radiation_zone)."""
    if distance_re < INNER_BELT_START_RE:
        return "LOW_EARTH"
    if distance_re < OUTER_BELT_START_RE:
        return "INNER_BELT"
    if distance_re < DEEP_SPACE_START_RE:
        return "OUTER_BELT"
    return "DEEP_SPACE"


def _ugy_per_minute_to_rad_s(rate: float | np.ndarray) -> float | np.ndarray:
    return rate * RAD_PER_MICROGRAY / SECONDS_PER_MINUTE


def _shell_rate_ugy_min(shell: BeltShell, distance_re: float | np.ndarray) -> float | np.ndarray:
    return shell.peak_ugy_min * np.exp(-0.5 * ((distance_re - shell.center_re) / shell.width_re) ** 2)


def compute_belt_dose_rate_rad_s(distance_re: float | np.ndarray) -> float | np.ndarray:
    """Combined inner and outer belt dose rate (rad/s) at a geocentric distance."""
    return _ugy_per_minute_to_rad_s(
        _shell_rate_ugy_min(INNER_BELT, distance_re) + _shell_rate_ugy_min(OUTER_BELT, distance_re)
    )


def compute_blocked_sky_fraction(
    distance_km: float | np.ndarray,
    body_radius_km: float,
) -> float | np.ndarray:
    """Fraction of the full sky covered by a sphere, seen from a distance to its centre.

    At or inside the surface the sphere covers half the sky.
    """
    sine = body_radius_km / np.maximum(distance_km, body_radius_km)
    return (1.0 - np.sqrt(1.0 - sine**2)) / 2.0


def compute_gcr_dose_rate_rad_s(
    position_km: np.ndarray,
    moon_position_km: np.ndarray,
) -> float | np.ndarray:
    """Cosmic-ray dose rate (rad/s), reduced by the sky Earth and the Moon block."""
    earth = compute_blocked_sky_fraction(np.linalg.norm(position_km, axis=-1), EARTH_RADIUS_KM)
    moon = compute_blocked_sky_fraction(
        np.linalg.norm(position_km - moon_position_km, axis=-1), MOON_RADIUS_KM
    )
    return _ugy_per_minute_to_rad_s(GCR_FREE_SPACE_UGY_MIN * (1.0 - earth - moon))


def _cumulative_krad(rate_rad_s: np.ndarray, seconds: np.ndarray) -> np.ndarray:
    """Trapezoidal integral of a dose rate, starting from zero."""
    steps = 0.5 * (rate_rad_s[1:] + rate_rad_s[:-1]) * np.diff(seconds)
    return np.concatenate(([0.0], np.cumsum(steps))) / RAD_PER_KRAD


def _unix_seconds(t: datetime) -> float:
    """Unix time; a naive time is read as UTC, as the OEM reader does."""
    return (t if t.tzinfo else t.replace(tzinfo=UTC)).timestamp()


@dataclass(frozen=True, eq=False)
class DoseProfile:
    """Dose along an OEM arc on a fixed time grid; a pure function of timestamp."""

    seconds: np.ndarray
    belt_rate_rad_s: np.ndarray
    gcr_rate_rad_s: np.ndarray
    cumulative_belt_krad: np.ndarray
    cumulative_gcr_krad: np.ndarray

    @classmethod
    def from_ephemeris(cls, ephemeris: OemEphemeris, step_s: float = DOSE_GRID_STEP_S) -> "DoseProfile":
        start, stop = float(ephemeris.epochs[0]), float(ephemeris.epochs[-1])
        seconds = np.linspace(start, stop, ceil((stop - start) / step_s) + 1)
        positions = np.column_stack(
            [np.interp(seconds, ephemeris.epochs, ephemeris.positions[:, axis]) for axis in range(3)]
        )
        belt = compute_belt_dose_rate_rad_s(np.linalg.norm(positions, axis=1) / EARTH_RADIUS_KM)
        gcr = compute_gcr_dose_rate_rad_s(positions, compute_moon_positions_km(seconds))
        return cls(seconds, belt, gcr, _cumulative_krad(belt, seconds), _cumulative_krad(gcr, seconds))

    def at(self, t: datetime) -> DoseSample:
        """Dose at time t. Before the arc the total is 0; after it, the total holds."""
        now = _unix_seconds(t)
        cumulative_belt = float(np.interp(now, self.seconds, self.cumulative_belt_krad))
        cumulative_gcr = float(np.interp(now, self.seconds, self.cumulative_gcr_krad))
        return DoseSample(
            belt_rate_rad_s=float(np.interp(now, self.seconds, self.belt_rate_rad_s)),
            gcr_rate_rad_s=float(np.interp(now, self.seconds, self.gcr_rate_rad_s)),
            cumulative_krad=cumulative_belt + cumulative_gcr,
            cumulative_belt_krad=cumulative_belt,
        )


def compute_instant_dose(position_km: np.ndarray, t: datetime) -> DoseSample:
    """Dose rates at one position, for placeholder-orbit runs with no arc to integrate."""
    distance_re = float(np.linalg.norm(position_km)) / EARTH_RADIUS_KM
    return DoseSample(
        belt_rate_rad_s=float(compute_belt_dose_rate_rad_s(distance_re)),
        gcr_rate_rad_s=float(compute_gcr_dose_rate_rad_s(position_km, compute_moon_position_km(t))),
        cumulative_krad=0.0,
        cumulative_belt_krad=0.0,
    )
