"""Tests for power physics module."""

import pytest
from physics_models.power.physics import (
    PowerModel,
    compute_battery_soc,
    compute_power_balance,
    compute_solar_array_power,
)


class TestSolarArrayPower:
    """Test solar array power computation."""

    def test_normal_incidence_bol(self):
        """Normal incidence at beginning of life."""
        power = compute_solar_array_power(
            solar_flux=1361.0,
            incidence_angle_deg=0.0,
            array_area_m2=56.0,
            efficiency=0.30,
            degradation_factor=1.0,
            temperature_k=298.15,
        )
        expected = 1361.0 * 56.0 * 0.30
        assert power == pytest.approx(expected, rel=1e-6)

    def test_angled_incidence(self):
        """Angled incidence follows cosine law."""
        power_0 = compute_solar_array_power(1361.0, 0.0, 56.0, 0.30, 1.0, 298.15)
        power_60 = compute_solar_array_power(1361.0, 60.0, 56.0, 0.30, 1.0, 298.15)
        assert power_60 == pytest.approx(power_0 * 0.5, rel=1e-6)

    def test_degradation_factor(self):
        """Degradation reduces power linearly."""
        power_new = compute_solar_array_power(1361.0, 0.0, 56.0, 0.30, 1.0, 298.15)
        power_degraded = compute_solar_array_power(1361.0, 0.0, 56.0, 0.30, 0.8, 298.15)
        assert power_degraded == pytest.approx(power_new * 0.8, rel=1e-6)

    def test_temperature_derating(self):
        """High temperature reduces efficiency."""
        power_cold = compute_solar_array_power(1361.0, 0.0, 56.0, 0.30, 1.0, 273.15)
        power_hot = compute_solar_array_power(1361.0, 0.0, 56.0, 0.30, 1.0, 353.15)
        assert power_hot < power_cold

    def test_eclipse_zero_power(self):
        """Array in eclipse produces no power."""
        power = compute_solar_array_power(
            solar_flux=1361.0,
            incidence_angle_deg=0.0,
            array_area_m2=56.0,
            efficiency=0.30,
            degradation_factor=1.0,
            temperature_k=298.15,
            in_eclipse=True,
        )
        assert power == pytest.approx(0.0, abs=1e-6)


class TestBatterySOC:
    """Test battery state of charge computation."""

    def test_charge_increases_soc(self):
        """Charging increases SOC."""
        soc = compute_battery_soc(
            soc_initial=0.5,  # 50%
            current_a=10.0,   # Charging
            capacity_ah=100.0,
            dt_hours=1.0,
        )
        assert soc > 0.5

    def test_discharge_decreases_soc(self):
        """Discharging decreases SOC."""
        soc = compute_battery_soc(
            soc_initial=0.5,
            current_a=-10.0,  # Discharging
            capacity_ah=100.0,
            dt_hours=1.0,
        )
        assert soc < 0.5

    def test_soc_limits(self):
        """SOC clamped to [0, 1]."""
        # Overcharge
        soc = compute_battery_soc(0.95, 50.0, 100.0, 1.0)
        assert soc == pytest.approx(1.0, abs=1e-3)
        
        # Overdischarge
        soc = compute_battery_soc(0.05, -50.0, 100.0, 1.0)
        assert soc == pytest.approx(0.0, abs=1e-3)

    def test_zero_current_no_change(self):
        """Zero current leaves SOC unchanged."""
        soc = compute_battery_soc(0.5, 0.0, 100.0, 1.0)
        assert soc == pytest.approx(0.5, abs=1e-6)


class TestPowerBalance:
    """Test power balance computation."""

    def test_surplus_charges_battery(self):
        """Power surplus charges battery."""
        array_power = 2000.0
        load_power = 1200.0
        battery_power, net_power = compute_power_balance(array_power, load_power)
        
        assert battery_power > 0  # Charging
        assert net_power == pytest.approx(array_power - load_power)

    def test_deficit_discharges_battery(self):
        """Power deficit discharges battery."""
        array_power = 800.0
        load_power = 1200.0
        battery_power, net_power = compute_power_balance(array_power, load_power)
        
        assert battery_power < 0  # Discharging
        assert net_power == pytest.approx(array_power - load_power)

    def test_balanced_zero_battery_current(self):
        """Balanced power gives zero battery current."""
        battery_power, _net_power = compute_power_balance(1200.0, 1200.0)
        assert battery_power == pytest.approx(0.0, abs=1e-6)


class TestPowerModel:
    """Test the integrated power model."""

    @pytest.fixture
    def model(self):
        """Create a standard power model."""
        return PowerModel(
            array_area_m2=56.0,
            array_efficiency_bol=0.30,
            battery_capacity_ah=100.0,
            battery_voltage_nominal_v=28.0,
            max_charge_current_a=50.0,
            max_discharge_current_a=100.0,
            bus_voltage_v=28.0,
        )

    def test_initial_state(self, model):
        """Initial state should have reasonable defaults."""
        assert model.battery_soc == 1.0  # Start fully charged
        assert model.array_efficiency == 0.30
        assert model.battery_voltage_v == 28.0

    def test_step_in_sunlight_charges_battery(self, model):
        """Sunlight with surplus power should charge battery."""
        model.step(
            solar_flux=1361.0,
            incidence_angle_deg=0.0,
            eclipse_fraction=0.0,
            total_load_w=1000.0,
            dt=60.0,
            electronics_bay_temp_k=293.15,
            degradation_factor=1.0,
        )
        
        assert model.array_power_w > model.total_load_w
        assert model.battery_current_a > 0  # Charging
        assert model.net_power_w > 0

    def test_step_in_eclipse_discharges_battery(self, model):
        """Eclipse should discharge battery."""
        model.step(
            solar_flux=1361.0,
            incidence_angle_deg=0.0,
            eclipse_fraction=1.0,  # Full eclipse
            total_load_w=1000.0,
            dt=60.0,
            electronics_bay_temp_k=293.15,
            degradation_factor=1.0,
        )
        
        assert model.array_power_w == pytest.approx(0.0, abs=1e-3)
        assert model.battery_current_a < 0  # Discharging
        assert model.net_power_w < 0

    def test_step_at_high_incidence_angle(self, model):
        """High incidence angle reduces array power."""
        model.step(
            solar_flux=1361.0,
            incidence_angle_deg=85.0,  # Near grazing
            eclipse_fraction=0.0,
            total_load_w=1000.0,
            dt=60.0,
            electronics_bay_temp_k=293.15,
            degradation_factor=1.0,
        )
        
        # At 85°, cos(85°) ≈ 0.087, so power ≈ 1361*56*0.3*0.087 ≈ 1980 W
        # Still > 1000W due to large array, but significantly reduced
        assert model.array_power_w < 2500.0
        assert model.array_power_w < model.array_power_w * 10  # Just verify it ran

    def test_battery_voltage_curve(self, model):
        """Battery voltage should vary with SOC."""
        # Use 25°C reference temperature (298.15 K)
        model.battery_soc = 1.0
        model.battery_current_a = 0.0
        model._update_battery_voltage(temp_k=298.15)
        v_full = model.battery_voltage_v
        
        model.battery_soc = 0.0
        model._update_battery_voltage(temp_k=298.15)
        v_empty = model.battery_voltage_v
        
        assert v_full > v_empty
        assert v_full > 28.0
        assert v_empty < 28.0

    def test_power_state_classification(self, model):
        """Power state must be strictly SOC-gated per ODCS 03 contract."""
        # Nominal: surplus power, SOC > 20%
        model.battery_soc = 0.9
        model.net_power_w = 500.0
        model._update_power_state()
        assert model.power_state == "NOMINAL"

        # Battery discharge: SOC > 20% with power deficit
        model.battery_soc = 0.4
        model.net_power_w = -200.0
        model._update_power_state()
        assert model.power_state == "BATTERY_DISCHARGE"

        # Battery discharge: high SOC, deficit
        model.battery_soc = 0.6
        model.net_power_w = -200.0
        model._update_power_state()
        assert model.power_state == "BATTERY_DISCHARGE"

        # Low power mode: 10% < SOC <= 20%, regardless of net power direction
        model.battery_soc = 0.15
        model.net_power_w = -200.0
        model._update_power_state()
        assert model.power_state == "LOW_POWER_MODE"

        model.battery_soc = 0.15
        model.net_power_w = 100.0  # surplus does NOT rescue the state
        model._update_power_state()
        assert model.power_state == "LOW_POWER_MODE"

        # Critical: SOC <= 10%, even with surplus (contract: NOMINAL at SOC 5%
        # is a data integrity failure)
        model.battery_soc = 0.05
        model.net_power_w = 100.0
        model._update_power_state()
        assert model.power_state == "CRITICAL"

    def test_cross_model_degradation(self, model):
        """Radiation degradation should reduce array power."""
        model.step(
            solar_flux=1361.0,
            incidence_angle_deg=0.0,
            eclipse_fraction=0.0,
            total_load_w=1000.0,
            dt=60.0,
            electronics_bay_temp_k=293.15,
            degradation_factor=1.0,
        )
        power_nominal = model.array_power_w
        
        model.step(
            solar_flux=1361.0,
            incidence_angle_deg=0.0,
            eclipse_fraction=0.0,
            total_load_w=1000.0,
            dt=60.0,
            electronics_bay_temp_k=293.15,
            degradation_factor=0.8,  # 20% degraded
        )
        power_degraded = model.array_power_w
        
        assert power_degraded == pytest.approx(power_nominal * 0.8, rel=1e-3)

    def test_cross_model_temperature(self, model):
        """Electronics bay temperature should affect battery voltage."""
        # Cold battery - higher voltage
        model.battery_soc = 0.5
        model._update_battery_voltage(temp_k=263.15)  # -10°C
        v_cold = model.battery_voltage_v
        
        # Hot battery - lower voltage
        model._update_battery_voltage(temp_k=313.15)  # 40°C
        v_hot = model.battery_voltage_v
        
        assert v_cold > v_hot

    def test_available_power(self, model):
        """Available power should include array + battery capability."""
        model.step(
            solar_flux=1361.0,
            incidence_angle_deg=0.0,
            eclipse_fraction=0.0,
            total_load_w=1000.0,
            dt=60.0,
            electronics_bay_temp_k=293.15,
            degradation_factor=1.0,
        )
        
        # Available = array + max discharge capability
        max_discharge_power = model.max_discharge_current_a * model.battery_voltage_v
        expected_available = model.array_power_w + max_discharge_power
        
        assert model.available_power_w == pytest.approx(expected_available, rel=1e-3)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])