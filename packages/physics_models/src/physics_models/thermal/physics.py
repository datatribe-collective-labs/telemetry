"""3-node lumped parameter thermal model for Orion spacecraft.

Nodes:
- Sun Face: External panel facing Sun
- Shadow Face: External panel facing deep space
- Electronics Bay: Internal compartment with avionics, batteries, etc.

Coupling: Conductive between nodes, radiative to space.
"""

from dataclasses import dataclass, field
from math import cos, radians

import numpy as np

# Physical constants
STEFAN_BOLTZMANN = 5.670374419e-8  # W/m^2/K^4


def compute_radiative_heat_transfer(
    eps1: float,
    area: float,
    T1: float,
    T2: float,
    F12: float = 1.0,
    eps2: float | None = None,
) -> float:
    """Compute net radiative heat transfer between two surfaces.

    Args:
        eps1: Emissivity of surface 1
        area: Surface area (m^2)
        T1: Temperature of surface 1 (K)
        T2: Temperature of surface 2 (K)
        F12: View factor from surface 1 to surface 2 (default 1.0 for space)
        eps2: Emissivity of surface 2 (default = eps1 for space)

    Returns:
        Heat transfer rate from surface 1 to surface 2 (W). Positive = surface 1 loses heat.
    """
    if eps2 is None:
        eps2 = eps1

    if F12 >= 1.0:  # Radiating to deep space (blackbody at T2)
        return eps1 * STEFAN_BOLTZMANN * area * (T1**4 - T2**4)
    else:
        # Two gray surfaces
        return F12 * area * STEFAN_BOLTZMANN * (T1**4 - T2**4) / (1/eps1 + 1/eps2 - 1)


def compute_conductive_heat_transfer(
    k: float,
    area: float,
    length: float,
    T1: float,
    T2: float,
) -> float:
    """Compute conductive heat transfer (Fourier's law).

    Args:
        k: Thermal conductivity (W/m·K)
        area: Cross-sectional area (m^2)
        length: Path length (m)
        T1: Temperature at hot side (K)
        T2: Temperature at cold side (K)

    Returns:
        Heat transfer rate from T1 to T2 (W). Positive = heat flows from T1 to T2.
    """
    return k * area * (T1 - T2) / length


def compute_solar_absorbed(
    alpha: float,
    area: float,
    solar_flux: float,
    incidence_angle_deg: float,
) -> float:
    """Compute absorbed solar power.

    Args:
        alpha: Solar absorptivity (0-1)
        area: Surface area (m^2)
        solar_flux: Solar flux at spacecraft (W/m^2)
        incidence_angle_deg: Angle between surface normal and Sun vector (degrees)

    Returns:
        Absorbed solar power (W).
    """
    if incidence_angle_deg >= 90.0:
        return 0.0
    cos_theta = max(0.0, cos(radians(incidence_angle_deg)))
    return alpha * area * solar_flux * cos_theta


def compute_thermal_equilibrium(
    solar_flux: float,
    alpha: float,
    eps: float,
    area: float,
    internal_power: float,
    view_factor_to_space: float = 1.0,
) -> float:
    """Compute steady-state temperature for a surface.

    Energy balance: α * S * A * cos(θ) + Q_int = ε * σ * A * F * T^4

    Args:
        solar_flux: Solar flux (W/m^2)
        alpha: Solar absorptivity
        eps: Infrared emissivity
        area: Surface area (m^2)
        internal_power: Internal heat dissipation (W)
        view_factor_to_space: View factor to deep space (0-1)

    Returns:
        Equilibrium temperature (K).
    """
    absorbed = alpha * solar_flux * area
    total_power = absorbed + internal_power
    return (total_power / (eps * STEFAN_BOLTZMANN * area * view_factor_to_space))**0.25


@dataclass
class ThermalModel3Node:
    """3-node lumped parameter thermal model.

    Nodes:
    - Sun Face: External panel facing Sun (high alpha, high eps)
    - Shadow Face: External panel facing deep space (low alpha, high eps)
    - Electronics Bay: Internal compartment (moderate alpha/eps, high C)

    Coupling conductances (W/K) represent thermal paths between nodes.
    """

    # Node thermal capacitance (J/K)
    C_sun_face: float
    C_shadow_face: float
    C_electronics_bay: float

    # Node surface areas (m^2)
    A_sun_face: float
    A_shadow_face: float
    A_electronics_bay: float

    # Node surface properties
    eps_sun_face: float
    eps_shadow_face: float
    eps_electronics_bay: float
    alpha_sun_face: float
    alpha_shadow_face: float
    alpha_electronics_bay: float

    # Conductive coupling conductances (W/K)
    K_sun_shadow: float  # Sun face <-> Shadow face
    K_sun_elec: float    # Sun face <-> Electronics bay
    K_shadow_elec: float # Shadow face <-> Electronics bay

    # Heater parameters (contract 02: setpoint −5 °C; power is a MODEL_ASSUMPTION)
    heater_power_w: float = 25.0
    heater_setpoint_k: float = 268.15  # -5°C per ODCS 02_thermal_model
    heater_deadband_k: float = 2.0

    # Current temperatures (K)
    T_sun_face_k: float = field(default=293.15, init=False)
    T_shadow_face_k: float = field(default=293.15, init=False)
    T_electronics_bay_k: float = field(default=293.15, init=False)

    # Heater state
    heater_active: bool = field(default=False, init=False)

    # Derived: radiative conductances to space (updated each step)
    _h_rad_sun: float = field(default=0.0, init=False)
    _h_rad_shadow: float = field(default=0.0, init=False)
    _h_rad_elec: float = field(default=0.0, init=False)

    @classmethod
    def from_config(cls, config: dict) -> "ThermalModel3Node":
        """Create model from configuration dictionary."""
        return cls(
            C_sun_face=config["sun_face"]["C"],
            C_shadow_face=config["shadow_face"]["C"],
            C_electronics_bay=config["electronics_bay"]["C"],
            A_sun_face=config["sun_face"]["A"],
            A_shadow_face=config["shadow_face"]["A"],
            A_electronics_bay=config["electronics_bay"]["A"],
            eps_sun_face=config["sun_face"]["eps"],
            eps_shadow_face=config["shadow_face"]["eps"],
            eps_electronics_bay=config["electronics_bay"]["eps"],
            alpha_sun_face=config["sun_face"]["alpha"],
            alpha_shadow_face=config["shadow_face"]["alpha"],
            alpha_electronics_bay=config["electronics_bay"]["alpha"],
            K_sun_shadow=config["K_sun_shadow"],
            K_sun_elec=config["K_sun_elec"],
            K_shadow_elec=config["K_shadow_elec"],
            heater_power_w=config.get("heater_power_w", 100.0),
            heater_setpoint_k=config.get("heater_setpoint_k", 283.15),
            heater_deadband_k=config.get("heater_deadband_k", 2.0),
        )

    def _update_radiative_conductances(self):
        """Update linearized radiative conductances to space.

        h_rad = 4 * ε * σ * T^3 (linearized about current temperature)
        """
        self._h_rad_sun = 4 * self.eps_sun_face * STEFAN_BOLTZMANN * self.A_sun_face * self.T_sun_face_k**3
        self._h_rad_shadow = 4 * self.eps_shadow_face * STEFAN_BOLTZMANN * self.A_shadow_face * self.T_shadow_face_k**3
        self._h_rad_elec = 4 * self.eps_electronics_bay * STEFAN_BOLTZMANN * self.A_electronics_bay * self.T_electronics_bay_k**3

    def compute_solar_absorbed(self, solar_flux: float, incidence_angle_deg: float) -> float:
        """Total solar power absorbed by sun face."""
        return compute_solar_absorbed(
            self.alpha_sun_face,
            self.A_sun_face,
            solar_flux,
            incidence_angle_deg,
        )

    def step(
        self,
        solar_flux: float,
        solar_incidence_angle_deg: float,
        eclipse_fraction: float,
        internal_power_w: float,
        dt: float,
    ) -> None:
        """Advance thermal model by one time step.

        Uses implicit (backward Euler) integration for stability. The step is
        automatically sub-cycled at max 10 s per substep: the linearized radiative
        integration loses accuracy for large dt (e.g. accelerated replay).

        Args:
            solar_flux: Solar flux at spacecraft (W/m^2)
            solar_incidence_angle_deg: Sun incidence angle on sun face (deg)
            eclipse_fraction: Fraction of orbit in eclipse (0-1)
            internal_power_w: Total internal power dissipation (W)
            dt: Time step (s)
        """
        n_sub = max(1, int(np.ceil(dt / 10.0)))
        dtc = dt / n_sub
        for _ in range(n_sub):
            self._substep(solar_flux, solar_incidence_angle_deg, eclipse_fraction, internal_power_w, dtc)

    def _substep(
        self,
        solar_flux: float,
        solar_incidence_angle_deg: float,
        eclipse_fraction: float,
        internal_power_w: float,
        dt: float,
    ) -> None:
        """Single implicit integration substep."""
        # Update linearized radiative conductances
        self._update_radiative_conductances()

        # Solar power absorbed (reduced by eclipse fraction)
        q_solar = self.compute_solar_absorbed(solar_flux, solar_incidence_angle_deg) * (1.0 - eclipse_fraction)

        # Heater logic
        if self.T_electronics_bay_k < self.heater_setpoint_k:
            self.heater_active = True
        elif self.T_electronics_bay_k > self.heater_setpoint_k + self.heater_deadband_k:
            self.heater_active = False
        q_heater = self.heater_power_w if self.heater_active else 0.0

        # Total heat into electronics bay
        q_elec_internal = internal_power_w + q_heater

        # Implicit integration: solve [C/dt + H] * dT = Q * dt
        # Where H is the conductance matrix

        # Conductance matrix (W/K)
        H = np.array([
            [self._h_rad_sun + self.K_sun_shadow + self.K_sun_elec, -self.K_sun_shadow, -self.K_sun_elec],
            [-self.K_sun_shadow, self._h_rad_shadow + self.K_sun_shadow + self.K_shadow_elec, -self.K_shadow_elec],
            [-self.K_sun_elec, -self.K_shadow_elec, self._h_rad_elec + self.K_sun_elec + self.K_shadow_elec],
        ])

        # Capacitance matrix (J/K)
        C = np.diag([self.C_sun_face, self.C_shadow_face, self.C_electronics_bay])

        # Heat input vector (W)
        Q = np.array([
            q_solar,  # Sun face gets solar
            0.0,      # Shadow face gets no direct solar
            q_elec_internal,  # Electronics bay gets internal power + heater
        ])

        # Current temperature vector
        T = np.array([self.T_sun_face_k, self.T_shadow_face_k, self.T_electronics_bay_k])

        # Space temperature (K)
        T_space = 3.0

        # Radiative heat loss to space (linearized)
        Q_rad = np.array([
            self._h_rad_sun * (T[0] - T_space),
            self._h_rad_shadow * (T[1] - T_space),
            self._h_rad_elec * (T[2] - T_space),
        ])

        # Conductive heat exchange between nodes, evaluated at current temperatures
        # (this is the coupling heat flow: without it the conductances only damp the update)
        Q_cond = np.array([
            self.K_sun_shadow * (T[1] - T[0]) + self.K_sun_elec * (T[2] - T[0]),
            self.K_sun_shadow * (T[0] - T[1]) + self.K_shadow_elec * (T[2] - T[1]),
            self.K_sun_elec * (T[0] - T[2]) + self.K_shadow_elec * (T[1] - T[2]),
        ])

        # Net heat input
        Q_net = Q + Q_cond - Q_rad

        # Implicit solve: (C/dt + H) * dT = Q_net
        # dT = (C/dt + H)^-1 * Q_net
        A_mat = C / dt + H
        dT = np.linalg.solve(A_mat, Q_net)

        # Update temperatures
        self.T_sun_face_k += dT[0]
        self.T_shadow_face_k += dT[1]
        self.T_electronics_bay_k += dT[2]

        # Clamp to physical limits
        self.T_sun_face_k = max(3.0, min(500.0, self.T_sun_face_k))
        self.T_shadow_face_k = max(3.0, min(500.0, self.T_shadow_face_k))
        self.T_electronics_bay_k = max(3.0, min(500.0, self.T_electronics_bay_k))

    def total_energy(self) -> float:
        """Total thermal energy stored in all nodes (J)."""
        return (
            self.C_sun_face * self.T_sun_face_k +
            self.C_shadow_face * self.T_shadow_face_k +
            self.C_electronics_bay * self.T_electronics_bay_k
        )

    def get_temperatures(self) -> dict[str, float]:
        """Get all node temperatures."""
        return {
            "sun_face_k": self.T_sun_face_k,
            "shadow_face_k": self.T_shadow_face_k,
            "electronics_bay_k": self.T_electronics_bay_k,
        }

    def get_heat_flows(self, solar_flux: float, incidence_angle_deg: float, eclipse_fraction: float) -> dict[str, float]:
        """Get current heat flows (W)."""
        q_solar = self.compute_solar_absorbed(solar_flux, incidence_angle_deg) * (1.0 - eclipse_fraction)
        q_heater = self.heater_power_w if self.heater_active else 0.0

        T = np.array([self.T_sun_face_k, self.T_shadow_face_k, self.T_electronics_bay_k])
        T_space = 3.0

        q_rad_sun = self._h_rad_sun * (T[0] - T_space)
        q_rad_shadow = self._h_rad_shadow * (T[1] - T_space)
        q_rad_elec = self._h_rad_elec * (T[2] - T_space)

        q_cond_sun_shadow = self.K_sun_shadow * (T[0] - T[1])
        q_cond_sun_elec = self.K_sun_elec * (T[0] - T[2])
        q_cond_shadow_elec = self.K_shadow_elec * (T[1] - T[2])

        return {
            "q_solar_absorbed_w": q_solar,
            "q_heater_w": q_heater,
            "q_rad_sun_w": q_rad_sun,
            "q_rad_shadow_w": q_rad_shadow,
            "q_rad_elec_w": q_rad_elec,
            "q_cond_sun_shadow_w": q_cond_sun_shadow,
            "q_cond_sun_elec_w": q_cond_sun_elec,
            "q_cond_shadow_elec_w": q_cond_shadow_elec,
        }

    def thermal_state(self) -> str:
        """Classify thermal state per ODCS 02_thermal_model quality rules.

        COLD_SURVIVAL: electronics bay < 249 K or any surface < 100 K.
        HOT_LIMIT: electronics bay > 310 K or sun face > 450 K.
        """
        T_elec = self.T_electronics_bay_k
        T_sun = self.T_sun_face_k
        T_shadow = self.T_shadow_face_k
        if T_elec < 249.0 or T_sun < 100.0 or T_shadow < 100.0:
            return "COLD_SURVIVAL"
        elif T_elec > 310.0 or T_sun > 450.0:
            return "HOT_LIMIT"
        else:
            return "NOMINAL"