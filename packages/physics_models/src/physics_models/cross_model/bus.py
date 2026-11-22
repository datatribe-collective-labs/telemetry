"""Cross-model coupling bus — 1-tick lag coupling between physics models.

This bus implements the coupling between physics models with a 1-tick lag
to avoid circular dependencies. Models read from the bus at tick N,
and write to it at the end of tick N for consumption at tick N+1.
"""

from dataclasses import dataclass, field

from contracts import (
    SyntheticCommsOutput,
    SyntheticCrossModelState,
    SyntheticPowerOutput,
    SyntheticRadiationOutput,
    SyntheticThermalOutput,
)


@dataclass
class CrossModelBus:
    """Coupling bus — outputs from tick N feed inputs to tick N+1.

    Thermal -> Power: electronics_bay_temp_k
    Power -> Thermal: power_dissipation_w
    Power -> Comms: power_state (in process only, not in the published message)
    Radiation -> Power: solar_array_degradation_factor
    Radiation -> Thermal: thermal_coating_alpha_factor, thermal_coating_eps_factor
    Radiation -> Comms: plasma_noise_factor (not modeled, stays 1.0)
    """

    # Thermal -> Power
    electronics_bay_temp_k: float = 293.15

    # Power -> Thermal
    power_dissipation_w: float = 0.0

    # Power headroom, published for monitoring (None before the first power tick)
    available_power_w: float | None = None

    # Power -> Comms (None before the first power tick: transmitter on)
    power_state: str | None = None

    # Radiation -> Power
    solar_array_degradation_factor: float = 1.0

    # Radiation -> Thermal
    thermal_coating_alpha_factor: float = 1.0
    thermal_coating_eps_factor: float = 1.0

    # Radiation -> Comms (contract 04). Plasma effects are not modeled, so this stays
    # 1.0 (no degradation); SyntheticRadiationOutput has no such field.
    plasma_noise_factor: float = 1.0

    # For building SyntheticCrossModelState output
    _last_thermal: SyntheticThermalOutput | None = field(default=None, repr=False)
    _last_power: SyntheticPowerOutput | None = field(default=None, repr=False)
    _last_comms: SyntheticCommsOutput | None = field(default=None, repr=False)
    _last_radiation: SyntheticRadiationOutput | None = field(default=None, repr=False)

    def update(
        self,
        thermal: SyntheticThermalOutput,
        power: SyntheticPowerOutput,
        comms: SyntheticCommsOutput,
        radiation: SyntheticRadiationOutput,
    ) -> None:
        """Called AFTER all physics models complete at tick N.
        Updates lagged state for consumption at tick N+1.
        """
        # Store for CrossModelState output
        self._last_thermal = thermal
        self._last_power = power
        self._last_comms = comms
        self._last_radiation = radiation

        # Update coupling variables for NEXT tick
        self.electronics_bay_temp_k = thermal.temp_electronics_bay_k
        self.power_dissipation_w = power.total_load_w
        self.available_power_w = power.available_power_w
        self.power_state = power.power_state
        self.solar_array_degradation_factor = radiation.solar_array_degradation
        self.thermal_coating_alpha_factor = radiation.thermal_alpha_degradation
        self.thermal_coating_eps_factor = radiation.thermal_eps_degradation

    def to_cross_model_state(self, timestamp_utc) -> SyntheticCrossModelState:
        """Build the cross-model state output for this tick."""
        return SyntheticCrossModelState(
            timestamp_utc=timestamp_utc,
            electronics_bay_temp_k=self.electronics_bay_temp_k,
            power_dissipation_w=self.power_dissipation_w,
            available_power_w=self.available_power_w if self.available_power_w is not None else 0.0,
            solar_array_degradation_factor=self.solar_array_degradation_factor,
            thermal_coating_alpha_factor=self.thermal_coating_alpha_factor,
            thermal_coating_eps_factor=self.thermal_coating_eps_factor,
            plasma_noise_factor=self.plasma_noise_factor,
        )

    def reset(self) -> None:
        """Reset to initial conditions."""
        self.electronics_bay_temp_k = 293.15
        self.power_dissipation_w = 0.0
        self.available_power_w = None
        self.power_state = None
        self.solar_array_degradation_factor = 1.0
        self.thermal_coating_alpha_factor = 1.0
        self.thermal_coating_eps_factor = 1.0
        self.plasma_noise_factor = 1.0
        self._last_thermal = None
        self._last_power = None
        self._last_comms = None
        self._last_radiation = None