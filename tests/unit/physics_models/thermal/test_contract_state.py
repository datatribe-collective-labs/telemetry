"""Contract-alignment tests for thermal state classification (ODCS 02)."""

import pytest
from physics_models.thermal.physics import ThermalModel3Node


@pytest.fixture
def model():
    return ThermalModel3Node(
        C_sun_face=20000.0, C_shadow_face=20000.0, C_electronics_bay=80000.0,
        A_sun_face=4.0, A_shadow_face=4.0, A_electronics_bay=2.0,
        eps_sun_face=0.85, eps_shadow_face=0.80, eps_electronics_bay=0.9,
        alpha_sun_face=0.92, alpha_shadow_face=0.15, alpha_electronics_bay=0.3,
        K_sun_shadow=0.2, K_sun_elec=2.0, K_shadow_elec=5.0,
    )


class TestThermalStatePerContract:
    """ODCS 02: COLD_SURVIVAL = bay<249K or surface<100K; HOT_LIMIT = bay>310K or sun>450K."""

    def test_nominal_within_bands(self, model):
        model.T_sun_face_k = 320.0
        model.T_shadow_face_k = 250.0
        model.T_electronics_bay_k = 293.15
        assert model.thermal_state() == "NOMINAL"

    def test_cold_survival_bay_below_249(self, model):
        model.T_sun_face_k = 320.0
        model.T_shadow_face_k = 250.0
        model.T_electronics_bay_k = 248.0
        assert model.thermal_state() == "COLD_SURVIVAL"

    def test_cold_survival_surface_below_100(self, model):
        model.T_sun_face_k = 320.0
        model.T_shadow_face_k = 99.0  # shadow surface cold-soak
        model.T_electronics_bay_k = 293.15
        assert model.thermal_state() == "COLD_SURVIVAL"

    def test_hot_limit_bay_above_310(self, model):
        model.T_electronics_bay_k = 311.0
        assert model.thermal_state() == "HOT_LIMIT"

    def test_hot_limit_sun_face_above_450(self, model):
        model.T_electronics_bay_k = 293.15
        model.T_sun_face_k = 451.0
        assert model.thermal_state() == "HOT_LIMIT"

    def test_heater_setpoint_is_268_15k_per_contract(self, model):
        """Contract 02 states the heater setpoint as −5 °C (268.15 K)."""
        assert model.heater_setpoint_k == pytest.approx(268.15)
        assert model.heater_power_w == pytest.approx(25.0)
