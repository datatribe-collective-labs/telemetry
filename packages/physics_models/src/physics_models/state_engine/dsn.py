"""DSN ground-station visibility of a spacecraft given in EME2000 (ODCS 01 dsn_visibility).

Each station is fixed on the rotating Earth (WGS-84). The spacecraft is moved from
EME2000 to the Earth-fixed frame with IAU 1976 precession and GMST (IAU 1982), and its
elevation is measured from the station's local horizon. Nutation, polar motion and
UT1-UTC are ignored (about 0.01 degrees at most).

A station also loses Orion while the Moon crosses the straight line between them. Light
travel time is ignored: the Moon moves about 1 km while a signal reaches Earth.
"""

from dataclasses import dataclass
from datetime import UTC, datetime
from math import asin, cos, degrees, radians, sin, sqrt, tau
from typing import Literal

import numpy as np

from physics_models.state_engine.moon import MOON_RADIUS_KM, compute_moon_position_km

WGS84_A_KM = 6378.137
WGS84_F = 1 / 298.257223563
ELEVATION_CUTOFF_DEG = 10.0  # contract 01

J2000 = datetime(2000, 1, 1, 12, tzinfo=UTC)
SECONDS_PER_DAY = 86_400.0
SECONDS_PER_JULIAN_CENTURY = 36_525 * SECONDS_PER_DAY
ARCSEC_TO_RAD = radians(1 / 3600)

DsnView = Literal["CLEAR", "MOON_BLOCKED", "OUT_OF_VIEW"]


@dataclass(frozen=True)
class DsnSite:
    site: str
    complex: str
    east_longitude_deg: float
    latitude_deg: float
    altitude_km: float


# Same coordinates as pipelines.ingest.jpl_dsn_geometry (copied: the packages stay
# independent), so the model can be compared with the Horizons rows for these sites.
DSN_SITES: tuple[DsnSite, ...] = (
    DsnSite("DSS-14", "Goldstone", 243.1105, 35.4259, 1.002),
    DsnSite("DSS-43", "Canberra", 148.9813, -35.4024, 0.689),
    DsnSite("DSS-63", "Madrid", 355.7520, 40.4313, 0.865),
)


def _rotation_z(angle_rad: float) -> np.ndarray:
    """Frame rotation about z (rotates the axes, not the vector)."""
    c, s = cos(angle_rad), sin(angle_rad)
    return np.array([[c, s, 0.0], [-s, c, 0.0], [0.0, 0.0, 1.0]])


def _rotation_y(angle_rad: float) -> np.ndarray:
    """Frame rotation about y (rotates the axes, not the vector)."""
    c, s = cos(angle_rad), sin(angle_rad)
    return np.array([[c, 0.0, -s], [0.0, 1.0, 0.0], [s, 0.0, c]])


def _julian_centuries(t: datetime) -> float:
    """Julian centuries since J2000; a naive time is read as UTC, as the OEM reader does."""
    aware = t if t.tzinfo else t.replace(tzinfo=UTC)
    return (aware - J2000).total_seconds() / SECONDS_PER_JULIAN_CENTURY


def compute_gmst_rad(t: datetime) -> float:
    """Greenwich mean sidereal time (IAU 1982), radians in [0, 2π), with UT1 ≈ UTC."""
    c = _julian_centuries(t)
    seconds = (
        67_310.54841
        + (876_600.0 * 3600 + 8_640_184.812866) * c
        + 0.093104 * c**2
        - 6.2e-6 * c**3
    )
    return (seconds % SECONDS_PER_DAY) / SECONDS_PER_DAY * tau


def compute_precession_matrix(t: datetime) -> np.ndarray:
    """IAU 1976 precession: rotates an EME2000 vector to the mean equator of date."""
    c = _julian_centuries(t)
    zeta = (2306.2181 * c + 0.30188 * c**2 + 0.017998 * c**3) * ARCSEC_TO_RAD
    z = (2306.2181 * c + 1.09468 * c**2 + 0.018203 * c**3) * ARCSEC_TO_RAD
    theta = (2004.3109 * c - 0.42665 * c**2 - 0.041833 * c**3) * ARCSEC_TO_RAD
    return _rotation_z(-z) @ _rotation_y(theta) @ _rotation_z(-zeta)


def eme2000_to_earth_fixed(position_km: np.ndarray, t: datetime) -> np.ndarray:
    """Rotate an EME2000 position to the Earth-fixed frame at time t."""
    return _rotation_z(compute_gmst_rad(t)) @ compute_precession_matrix(t) @ position_km


def compute_site_position(site: DsnSite) -> tuple[np.ndarray, np.ndarray]:
    """Earth-fixed station position (km) and its local "up" unit vector (WGS-84)."""
    lat, lon = radians(site.latitude_deg), radians(site.east_longitude_deg)
    e2 = WGS84_F * (2 - WGS84_F)
    n = WGS84_A_KM / sqrt(1 - e2 * sin(lat) ** 2)
    up = np.array([cos(lat) * cos(lon), cos(lat) * sin(lon), sin(lat)])
    position = np.array(
        [
            (n + site.altitude_km) * cos(lat) * cos(lon),
            (n + site.altitude_km) * cos(lat) * sin(lon),
            (n * (1 - e2) + site.altitude_km) * sin(lat),
        ]
    )
    return position, up


def compute_site_elevation_deg(site: DsnSite, sc_pos_km: np.ndarray, t: datetime) -> float:
    """Geometric elevation of the spacecraft above the station's local horizon (degrees)."""
    site_pos, up = compute_site_position(site)
    line_of_sight = eme2000_to_earth_fixed(sc_pos_km, t) - site_pos
    sin_elevation = float(np.dot(up, line_of_sight) / np.linalg.norm(line_of_sight))
    return degrees(asin(max(-1.0, min(1.0, sin_elevation))))


def is_line_of_sight_blocked(
    start_km: np.ndarray,
    end_km: np.ndarray,
    body_center_km: np.ndarray,
    body_radius_km: float,
) -> bool:
    """True if the straight segment from start to end passes through the sphere."""
    segment = end_km - start_km
    fraction = np.dot(body_center_km - start_km, segment) / np.dot(segment, segment)
    closest_point = start_km + min(1.0, max(0.0, fraction)) * segment
    return bool(np.linalg.norm(body_center_km - closest_point) < body_radius_km)


def is_site_visible(
    site: DsnSite,
    sc_pos_km: np.ndarray,
    t: datetime,
    cutoff_deg: float = ELEVATION_CUTOFF_DEG,
) -> bool:
    """True if the spacecraft is above the site's cutoff and the Moon is not in the way."""
    if compute_site_elevation_deg(site, sc_pos_km, t) < cutoff_deg:
        return False
    site_pos, _ = compute_site_position(site)
    return not is_line_of_sight_blocked(
        site_pos,
        eme2000_to_earth_fixed(sc_pos_km, t),
        eme2000_to_earth_fixed(compute_moon_position_km(t), t),
        MOON_RADIUS_KM,
    )


def compute_dsn_view(
    sc_pos_km: np.ndarray,
    t: datetime,
    cutoff_deg: float = ELEVATION_CUTOFF_DEG,
) -> DsnView:
    """CLEAR if a complex can see the spacecraft, MOON_BLOCKED if the Moon blocks every
    complex above its cutoff, OUT_OF_VIEW if none is above it."""
    in_view = [s for s in DSN_SITES if compute_site_elevation_deg(s, sc_pos_km, t) >= cutoff_deg]
    if not in_view:
        return "OUT_OF_VIEW"
    if any(is_site_visible(site, sc_pos_km, t, cutoff_deg) for site in in_view):
        return "CLEAR"
    return "MOON_BLOCKED"


def is_dsn_visible(
    sc_pos_km: np.ndarray,
    t: datetime,
    cutoff_deg: float = ELEVATION_CUTOFF_DEG,
) -> bool:
    """True if at least one DSN complex has a clear view of the spacecraft."""
    return compute_dsn_view(sc_pos_km, t, cutoff_deg) == "CLEAR"
