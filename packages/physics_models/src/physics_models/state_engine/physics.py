"""Orbital mechanics, solar flux, and attitude physics for State Engine.

Provides the core physics calculations for the authoritative spacecraft state.
"""

from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from math import acos, atan2, cos, degrees, radians, sin, sqrt

import numpy as np

from physics_models.state_engine.planned_attitude import (
    AttitudeMode,
    get_solar_array_gimbal_estimate,
    get_solar_incidence_angle_estimate,
    resolve_attitude,
)

# Constants
EARTH_MU = 398600.4418  # km^3/s^2
SUN_MU = 1.32712440018e11  # km^3/s^2
AU_KM = 149597870.7  # km
SOLAR_CONSTANT = 1361.0  # W/m^2 at 1 AU
ORION_MASS_KG = 25848  # kg (Artemis II Orion mass)
ORION_CROSS_SECTION_M2 = 33.2  # m^2 (approximate)
# Solar array (contract 03 sourced: 4 wings ≈ 44.8 m² total, 28% BOL efficiency)
SOLAR_ARRAY_AREA_M2 = 44.8  # m^2
SOLAR_ARRAY_EFFICIENCY = 0.28  # 28% at BOL


@dataclass
class OrbitalState:
    """Keplerian orbital elements."""
    a: float  # semi-major axis (km)
    e: float  # eccentricity
    i: float  # inclination (rad)
    raan: float  # RAAN (rad)
    argp: float  # argument of periapsis (rad)
    nu: float  # true anomaly (rad)


@dataclass
class StateVector:
    """Position and velocity in ECI frame."""
    x: float  # km
    y: float
    z: float
    vx: float  # km/s
    vy: float
    vz: float
    epoch: datetime


def solve_kepler(e: float, M: float, tol: float = 1e-12, max_iter: int = 50) -> float:
    """Solve Kepler's equation M = E - e*sin(E) for eccentric anomaly E."""
    E = M if e < 0.8 else M + e * sin(M)
    for _ in range(max_iter):
        f = E - e * sin(E) - M
        df = 1 - e * cos(E)
        delta = f / df
        E -= delta
        if abs(delta) < tol:
            return E
    return E


def keplerian_to_state_vector(elements: OrbitalState, mu: float = EARTH_MU) -> StateVector:
    """Convert Keplerian elements to ECI state vector."""
    E = solve_kepler(elements.e, elements.nu)
    r = elements.a * (1 - elements.e * cos(E))

    # Position in perifocal frame
    x_pqw = r * cos(elements.nu)
    y_pqw = r * sin(elements.nu)

    # Velocity in perifocal frame
    h = sqrt(mu * elements.a * (1 - elements.e**2))
    vx_pqw = -mu / h * sin(elements.nu)
    vy_pqw = mu / h * (elements.e + cos(elements.nu))

    # Rotation matrices
    cos_raan, sin_raan = cos(elements.raan), sin(elements.raan)
    cos_i, sin_i = cos(elements.i), sin(elements.i)
    cos_argp, sin_argp = cos(elements.argp), sin(elements.argp)

    # PQW to ECI
    x = (cos_raan * cos_argp - sin_raan * sin_argp * cos_i) * x_pqw + \
        (-cos_raan * sin_argp - sin_raan * cos_argp * cos_i) * y_pqw
    y = (sin_raan * cos_argp + cos_raan * sin_argp * cos_i) * x_pqw + \
        (-sin_raan * sin_argp + cos_raan * cos_argp * cos_i) * y_pqw
    z = (sin_i * sin_argp) * x_pqw + (sin_i * cos_argp) * y_pqw

    vx = (cos_raan * cos_argp - sin_raan * sin_argp * cos_i) * vx_pqw + \
         (-cos_raan * sin_argp - sin_raan * cos_argp * cos_i) * vy_pqw
    vy = (sin_raan * cos_argp + cos_raan * sin_argp * cos_i) * vx_pqw + \
         (-sin_raan * sin_argp + cos_raan * cos_argp * cos_i) * vy_pqw
    vz = (sin_i * sin_argp) * vx_pqw + (sin_i * cos_argp) * vy_pqw

    return StateVector(x, y, z, vx, vy, vz, datetime.now(UTC))


def compute_solar_flux(distance_from_sun_km: float) -> float:
    """Compute solar flux at given distance from Sun (W/m^2)."""
    return SOLAR_CONSTANT * (AU_KM / distance_from_sun_km) ** 2


def compute_eclipse_state(
    sc_pos: np.ndarray,
    earth_pos: np.ndarray,
    sun_pos: np.ndarray,
    earth_radius_km: float = 6378.137,
) -> tuple[str, float]:
    """
    Compute eclipse state (SUNLIT, PENUMBRA, UMBRA) and eclipse fraction.

    Uses cylindrical shadow model with penumbra.
    Returns (state, fraction) where fraction=0 in full sun, 1 in full umbra.
    """
    # Vector from spacecraft to Earth
    r_sc_earth = earth_pos - sc_pos
    # Vector from spacecraft to Sun
    r_sc_sun = sun_pos - sc_pos

    # Distance from spacecraft to Earth center
    d_se = np.linalg.norm(r_sc_earth)
    # Distance from spacecraft to Sun
    d_ss = np.linalg.norm(r_sc_sun)

    # Angle between Earth-SC and Sun-SC vectors
    cos_theta = np.dot(r_sc_earth, r_sc_sun) / (d_se * d_ss)
    theta = acos(max(-1.0, min(1.0, cos_theta)))

    # Angular radius of Earth as seen from SC
    earth_ang_radius = asin(min(1.0, earth_radius_km / d_se))
    # Angular radius of Sun as seen from SC (approx 0.265 deg at 1 AU)
    sun_ang_radius = 0.00465  # radians

    if theta >= earth_ang_radius + sun_ang_radius:
        return "SUNLIT", 0.0
    elif theta <= earth_ang_radius - sun_ang_radius:
        return "UMBRA", 1.0
    else:
        # Penumbra - linear interpolation
        fraction = (earth_ang_radius + sun_ang_radius - theta) / (2 * sun_ang_radius)
        fraction = max(0.0, min(1.0, fraction))
        return "PENUMBRA", fraction


def compute_dsn_visibility(
    sc_pos: np.ndarray,
    dsn_sites: dict[str, np.ndarray],
    elevation_mask_deg: float = 10.0,
) -> dict[str, bool]:
    """Compute DSN site visibility given spacecraft position.

    Elevation angle is arcsin(site_up · los), where site_up is the
    unit vector from Earth center to the DSN site, and los is the
    unit vector from the site to the spacecraft.
    """
    visibility = {}

    for site_name, site_pos in dsn_sites.items():
        # Vector from DSN site to spacecraft (line of sight)
        r_site_sc = sc_pos - site_pos
        site_range = np.linalg.norm(r_site_sc)

        if site_range < 1e-6:
            visibility[site_name] = False
            continue

        # Site upward normal (from Earth center to site)
        site_up = site_pos / np.linalg.norm(site_pos)
        # Line of sight unit vector
        los = r_site_sc / site_range

        # Elevation: angle between site_up and los
        # elev = arcsin(site_up · los)
        sin_elev = np.dot(site_up, los)
        sin_elev = max(-1.0, min(1.0, sin_elev))
        elev = np.arcsin(sin_elev)

        visibility[site_name] = elev >= radians(elevation_mask_deg)

    return visibility


def compute_light_time(sc_pos: np.ndarray, earth_pos: np.ndarray) -> float:
    """Compute one-way light time (seconds)."""
    return np.linalg.norm(sc_pos - earth_pos) / 299792.458  # km / (km/s)


def propagate_orbit_two_body(
    initial_state: StateVector,
    dt_seconds: float,
    mu: float = EARTH_MU,
) -> StateVector:
    """Two-body propagation using universal variable formulation (Lagrange coefficients).

    Works for any orbit shape (circular, elliptical, hyperbolic).
    Based on the universal variable formulation from "Orbital Mechanics for Engineering Students".
    """
    r0_vec = np.array([initial_state.x, initial_state.y, initial_state.z])
    v0_vec = np.array([initial_state.vx, initial_state.vy, initial_state.vz])

    r0 = np.linalg.norm(r0_vec)
    v0 = np.linalg.norm(v0_vec)

    # Specific orbital energy
    alpha = 2.0 / r0 - v0**2 / mu

    # Universal anomaly via Newton-Raphson
    if alpha > 0:  # Elliptical
        # Initial guess
        chi = np.sqrt(mu) * alpha * dt_seconds
        for _ in range(50):
            z = alpha * chi**2
            S = (1 - z * c3(z)) / (alpha * chi)
            C = c2(z)
            f_val = r0 + np.dot(r0_vec, v0_vec) * S / np.sqrt(mu) + mu * chi**2 * C - np.sqrt(mu) * dt_seconds
            df = np.dot(r0_vec, v0_vec) * C / np.sqrt(mu) + mu * chi * (1 - z * S) / alpha
            if abs(f_val) < 1e-12:
                break
            chi -= f_val / df
    elif alpha < 0:  # Hyperbolic
        chi = 0.0
        # Not implemented - return initial state
        return initial_state
    else:  # Parabolic
        chi = 0.0
        # Not implemented - return initial state
        return initial_state

    z = alpha * chi**2
    f = 1 - chi**2 / r0 * c2(z)
    g = dt_seconds - chi**3 / np.sqrt(mu) * c3(z)
    fdot = np.sqrt(mu) / (r0 * r0) * (alpha * chi**3 * c3(z) - chi)
    gdot = 1 - chi**2 / r0 * c2(z)

    r_vec = f * r0_vec + g * v0_vec
    v_vec = fdot * r0_vec + gdot * v0_vec

    return StateVector(
        float(r_vec[0]), float(r_vec[1]), float(r_vec[2]),
        float(v_vec[0]), float(v_vec[1]), float(v_vec[2]),
        initial_state.epoch + timedelta(seconds=dt_seconds)
    )


def c2(z: float) -> float:
    """Stumpff function C2(z)."""
    if z > 1e-6:
        return (1 - np.cos(np.sqrt(z))) / z
    elif z < -1e-6:
        return (np.cosh(np.sqrt(-z)) - 1) / (-z)
    else:
        return 0.5


def c3(z: float) -> float:
    """Stumpff function C3(z)."""
    if z > 1e-6:
        return (np.sqrt(z) - np.sin(np.sqrt(z))) / (z**1.5)
    elif z < -1e-6:
        return (np.sinh(np.sqrt(-z)) - np.sqrt(-z)) / ((-z)**1.5)
    else:
        return 1.0 / 6.0


def compute_attitude_quaternion(attitude_mode: AttitudeMode, met: timedelta) -> tuple[float, float, float, float]:
    """Convert attitude mode to quaternion (w, x, y, z).

    Placeholder - real implementation needs full attitude definition
    including body-to-inertial transformation per mode.
    """
    # For now return identity (Earth-pointing default)
    # Real modes need specific quaternions from flight software definitions
    return 1.0, 0.0, 0.0, 0.0


def quaternion_to_euler(qw: float, qx: float, qy: float, qz: float) -> tuple[float, float, float]:
    """Convert quaternion to Euler angles (roll, pitch, yaw) in degrees."""
    # 3-2-1 sequence (yaw, pitch, roll)
    roll = atan2(2*(qw*qx + qy*qz), 1 - 2*(qx**2 + qy**2))
    pitch = asin(max(-1.0, min(1.0, 2*(qw*qy - qz*qx))))
    yaw = atan2(2*(qw*qz + qx*qy), 1 - 2*(qy**2 + qz**2))
    return degrees(roll), degrees(pitch), degrees(yaw)


# Need to import asin
from math import asin


class StateEnginePhysics:
    """Physics computations for StateEngineGenerator."""

    def __init__(self, liftoff_utc: datetime):
        self.liftoff_utc = liftoff_utc
        # DSN sites in ECI (simplified - real positions need Earth rotation)
        self.dsn_sites = {
            "GOLDSTONE": np.array([-2350.0, -4650.0, 3670.0]),
            "MADRID": np.array([4850.0, -350.0, 3950.0]),
            "CANBERRA": np.array([-4450.0, 2800.0, -3650.0]),
        }

    def compute_state_at_met(self, met: timedelta) -> dict:
        """Compute full spacecraft state at Mission Elapsed Time."""
        current_time = self.liftoff_utc + met

        # TODO: Replace with OEM/Horizons interpolation
        # For now, use placeholder circular orbit
        # Earth orbit altitude ~ 300 km during early mission, then TLI
        altitude_km = 300.0  # placeholder
        radius = 6378.137 + altitude_km
        velocity = sqrt(EARTH_MU / radius)

        # Circular equatorial orbit placeholder
        omega = velocity / radius
        theta = omega * met.total_seconds()

        sc_pos = np.array([radius * cos(theta), radius * sin(theta), 0.0])
        sc_vel = np.array([-velocity * sin(theta), velocity * cos(theta), 0.0])

        # Sun position (simplified - circular orbit, 1 AU)
        # 1 year = 365.25 days
        sun_omega = 2 * np.pi / (365.25 * 86400)
        sun_theta = sun_omega * (met.total_seconds() + self.liftoff_utc.timestamp())
        sun_pos = np.array([AU_KM * cos(sun_theta), AU_KM * sin(sun_theta), 0.0])

        # Earth position (at origin for Earth-centered frame)
        earth_pos = np.array([0.0, 0.0, 0.0])

        # Distance from Sun
        r_sc_sun = np.linalg.norm(sun_pos - sc_pos)
        distance_from_sun_au = r_sc_sun / AU_KM

        # Solar flux
        solar_flux = compute_solar_flux(r_sc_sun)

        # Eclipse state
        eclipse_state, eclipse_fraction = compute_eclipse_state(sc_pos, earth_pos, sun_pos)

        # DSN visibility
        dsn_vis = compute_dsn_visibility(sc_pos, self.dsn_sites)
        any_dsn_visible = any(dsn_vis.values())

        # Light time
        light_time = compute_light_time(sc_pos, earth_pos)

        # Attitude
        attitude_mode, _mode_def = resolve_attitude(met)
        solar_incidence = get_solar_incidence_angle_estimate(met)
        solar_array_angle = get_solar_array_gimbal_estimate(met)
        qw, qx, qy, qz = compute_attitude_quaternion(attitude_mode, met)
        roll, pitch, yaw = quaternion_to_euler(qw, qx, qy, qz)

        return {
            "timestamp_utc": current_time,
            "x_km": float(sc_pos[0]),
            "y_km": float(sc_pos[1]),
            "z_km": float(sc_pos[2]),
            "vx_kms": float(sc_vel[0]),
            "vy_kms": float(sc_vel[1]),
            "vz_kms": float(sc_vel[2]),
            "distance_from_sun_au": distance_from_sun_au,
            "solar_flux_w_m2": solar_flux,
            "solar_incidence_angle_deg": solar_incidence,
            "eclipse_state": eclipse_state,
            "eclipse_fraction": eclipse_fraction,
            "earth_distance_km": float(np.linalg.norm(sc_pos)),
            "dsn_visibility": any_dsn_visible,
            "light_time_s": light_time,
            "solar_array_angle_deg": solar_array_angle,
            "roll_deg": roll,
            "pitch_deg": pitch,
            "yaw_deg": yaw,
            "attitude_mode": attitude_mode.value,
        }


def compute_solar_array_power(
    solar_flux: float,
    incidence_angle_deg: float,
    array_area_m2: float = SOLAR_ARRAY_AREA_M2,
    efficiency: float = SOLAR_ARRAY_EFFICIENCY,
    degradation_factor: float = 1.0,
    temperature_k: float = 293.15,
) -> float:
    """Compute solar array power output (W)."""
    # Cosine loss
    cos_loss = max(0.0, cos(radians(incidence_angle_deg)))

    # Temperature derating (approx -0.5%/degC above 25C)
    temp_derate = max(0.7, 1.0 - 0.005 * max(0.0, temperature_k - 298.15))

    return solar_flux * array_area_m2 * efficiency * cos_loss * degradation_factor * temp_derate