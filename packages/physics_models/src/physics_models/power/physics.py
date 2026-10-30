"""Power model for Orion spacecraft.

Components:
- Solar array (two wings, 28 m² each = 56 m² total)
- Li-ion battery (100 Ah, 28 V nominal)
- Power distribution unit (PDU)
- Loads: avionics, thermal, comms, propulsion, payload
"""

from dataclasses import dataclass, field
from math import cos, radians


def compute_solar_array_power(
    solar_flux: float,
    incidence_angle_deg: float,
    array_area_m2: float,
    efficiency: float,
    degradation_factor: float,
    temperature_k: float,
    in_eclipse: bool = False,
) -> float:
    """Compute solar array power output.

    Args:
        solar_flux: Solar flux at spacecraft (W/m²)
        incidence_angle_deg: Angle between array normal and Sun vector (deg)
        array_area_m2: Total array area (m²)
        efficiency: Array efficiency at BOL, 25°C (0-1)
        degradation_factor: Radiation degradation factor (0-1, 1.0 = new)
        temperature_k: Array temperature (K)
        in_eclipse: Whether array is in eclipse

    Returns:
        Array power output (W).
    """
    if in_eclipse:
        return 0.0

    # Cosine loss
    if incidence_angle_deg >= 90.0:
        return 0.0
    cos_loss = max(0.0, cos(radians(incidence_angle_deg)))

    # Temperature derating: ~-0.5%/°C above 25°C
    temp_c = temperature_k - 273.15
    temp_derate = max(0.5, 1.0 - 0.005 * max(0.0, temp_c - 25.0))

    return solar_flux * array_area_m2 * efficiency * cos_loss * degradation_factor * temp_derate


def compute_battery_soc(
    soc_initial: float,
    current_a: float,
    capacity_ah: float,
    dt_hours: float,
) -> float:
    """Compute battery state of charge.

    Args:
        soc_initial: Initial SOC (0-1)
        current_a: Battery current (A), positive = charging
        capacity_ah: Battery capacity (Ah)
        dt_hours: Time step (hours)

    Returns:
        New SOC (0-1).
    """
    # Coulomb counting: ΔSOC = I * dt / Capacity
    delta_soc = current_a * dt_hours / capacity_ah
    soc_new = soc_initial + delta_soc
    return max(0.0, min(1.0, soc_new))


def compute_power_balance(
    array_power_w: float,
    load_power_w: float,
) -> tuple[float, float]:
    """Compute power balance.

    Args:
        array_power_w: Solar array power (W)
        load_power_w: Total load power (W)

    Returns:
        (battery_power_w, net_power_w) where battery_power > 0 = charging.
    """
    net_power = array_power_w - load_power_w
    battery_power = net_power  # Battery absorbs/provides the difference
    return battery_power, net_power


@dataclass
class PowerModel:
    """Integrated power system model."""

    # Solar array parameters (contract-sourced: 4 wings, 44.8 m² total, 28% BOL —
    # gives the ODCS 03 physics ceiling 17,072-17,100 W at 1 AU face-on;
    # the 11.2 kW figure is the design point at realistic operating conditions)
    array_area_m2: float = 44.8           # 4 wings (A.T.L.A.S / contract 03)
    array_efficiency_bol: float = 0.28    # 28% at BOL, 25°C
    array_temp_coeff: float = -0.005      # -0.5%/°C

    # Battery parameters
    battery_capacity_ah: float = 100.0    # 100 Ah
    battery_voltage_nominal_v: float = 28.0
    battery_resistance_ohm: float = 0.01  # Internal resistance
    max_charge_current_a: float = 50.0
    max_discharge_current_a: float = 100.0

    # Bus
    bus_voltage_v: float = 28.0

    # State
    battery_soc: float = field(default=1.0, init=False)
    array_efficiency: float = field(default=0.30, init=False)
    battery_voltage_v: float = field(default=28.0, init=False)
    battery_current_a: float = field(default=0.0, init=False)
    array_power_w: float = field(default=0.0, init=False)
    total_load_w: float = field(default=0.0, init=False)
    net_power_w: float = field(default=0.0, init=False)
    available_power_w: float = field(default=0.0, init=False)
    power_state: str = field(default="NOMINAL", init=False)

    def _update_battery_voltage(self, temp_k: float = 293.15):
        """Update battery voltage based on SOC and temperature.

        Uses simplified Li-ion voltage curve:
        V = V_nom + (SOC - 0.5) * 0.8 + (25 - T_c) * 0.02
        """
        soc = self.battery_soc
        temp_c = temp_k - 273.15

        # Open circuit voltage vs SOC (simplified linear approximation)
        # Li-ion: ~3.0-4.2V per cell, 8 cells in series = 24-33.6V
        # Nominal 28V at 50% SOC
        v_ocv = 28.0 + (soc - 0.5) * 0.8

        # Temperature effect: ~20mV/°C per cell, 8 cells = 160mV/°C
        # Cold = higher voltage
        v_temp = (25.0 - temp_c) * 0.16

        self.battery_voltage_v = v_ocv + v_temp

        # Apply internal resistance drop under load
        # V_terminal = V_ocv - I * R_internal
        self.battery_voltage_v -= self.battery_current_a * self.battery_resistance_ohm

        # Clamp
        self.battery_voltage_v = max(20.0, min(34.0, self.battery_voltage_v))

    def _update_power_state(self):
        """Classify power system state per ODCS 03 power_model_output.

        State is strictly SOC-gated (contract: a NOMINAL state with
        battery_soc_pct = 5 is a data integrity failure):
            CRITICAL:         soc <= 10%
            LOW_POWER_MODE:   10% < soc <= 20%
            BATTERY_DISCHARGE: soc > 20% AND net_power < 0
            NOMINAL:          soc > 20% AND net_power >= 0
        """
        soc_pct = self.battery_soc * 100.0
        if soc_pct <= 10.0:
            self.power_state = "CRITICAL"
        elif soc_pct <= 20.0:
            self.power_state = "LOW_POWER_MODE"
        elif self.net_power_w < 0:
            self.power_state = "BATTERY_DISCHARGE"
        else:
            self.power_state = "NOMINAL"

    def step(
        self,
        solar_flux: float,
        incidence_angle_deg: float,
        eclipse_fraction: float,
        total_load_w: float,
        dt: float,
        electronics_bay_temp_k: float,
        degradation_factor: float = 1.0,
    ) -> None:
        """Advance power model by one time step.

        Args:
            solar_flux: Solar flux (W/m²)
            incidence_angle_deg: Array incidence angle (deg)
            eclipse_fraction: Fraction of step in eclipse (0-1)
            total_load_w: Total spacecraft load (W)
            dt: Time step (s)
            electronics_bay_temp_k: Battery temperature (K)
            degradation_factor: Array degradation factor (0-1)
        """
        self.total_load_w = total_load_w

        # Determine if in eclipse for this step
        in_eclipse = eclipse_fraction > 0.5

        # Compute array power
        self.array_power_w = compute_solar_array_power(
            solar_flux=solar_flux,
            incidence_angle_deg=incidence_angle_deg,
            array_area_m2=self.array_area_m2,
            efficiency=self.array_efficiency_bol,
            degradation_factor=degradation_factor,
            temperature_k=electronics_bay_temp_k,  # Use electronics bay temp as proxy
            in_eclipse=in_eclipse,
        )

        # Apply eclipse fraction (partial eclipse)
        if 0.0 < eclipse_fraction < 1.0:
            self.array_power_w *= (1.0 - eclipse_fraction)

        # Power balance
        self.net_power_w = self.array_power_w - total_load_w

        # Battery current (simplified: all net power goes to/from battery)
        # I = P / V
        if abs(self.battery_voltage_v) > 1.0:
            self.battery_current_a = self.net_power_w / self.battery_voltage_v
        else:
            self.battery_current_a = 0.0

        # Limit current
        self.battery_current_a = max(
            -self.max_discharge_current_a,
            min(self.max_charge_current_a, self.battery_current_a)
        )

        # Update SOC
        dt_hours = dt / 3600.0
        self.battery_soc = compute_battery_soc(
            self.battery_soc,
            self.battery_current_a,
            self.battery_capacity_ah,
            dt_hours,
        )

        # Update battery voltage
        self._update_battery_voltage(electronics_bay_temp_k)

        # Available power = array + max battery discharge capability
        max_discharge_power = self.max_discharge_current_a * self.battery_voltage_v
        self.available_power_w = self.array_power_w + max_discharge_power

        # Update power state
        self._update_power_state()

    def get_state(self) -> dict:
        """Get current power system state."""
        return {
            "array_power_w": self.array_power_w,
            "array_efficiency": self.array_efficiency,
            "total_load_w": self.total_load_w,
            "battery_soc_pct": self.battery_soc * 100.0,
            "battery_voltage_v": self.battery_voltage_v,
            "battery_current_a": self.battery_current_a,
            "net_power_w": self.net_power_w,
            "available_power_w": self.available_power_w,
            "power_state": self.power_state,
        }

    def reset(self):
        """Reset to initial conditions."""
        self.battery_soc = 1.0
        self.array_efficiency = self.array_efficiency_bol
        self.battery_voltage_v = self.battery_voltage_nominal_v
        self.battery_current_a = 0.0
        self.array_power_w = 0.0
        self.total_load_w = 0.0
        self.net_power_w = 0.0
        self.available_power_w = 0.0
        self.power_state = "NOMINAL"