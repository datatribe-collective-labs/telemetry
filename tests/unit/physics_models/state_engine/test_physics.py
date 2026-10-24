"""Tests for state_engine physics module."""

from datetime import UTC, datetime, timedelta

import numpy as np
import pytest
from physics_models.state_engine.physics import (
    AU_KM,
    SOLAR_CONSTANT,
    OrbitalState,
    StateEnginePhysics,
    compute_attitude_quaternion,
    compute_dsn_visibility,
    compute_eclipse_state,
    compute_light_time,
    compute_solar_array_power,
    compute_solar_flux,
    keplerian_to_state_vector,
    propagate_orbit_two_body,
    quaternion_to_euler,
    solve_kepler,
)


class TestSolveKepler:
    """Test Kepler equation solver."""

    def test_circular_orbit(self):
        """Circular orbit (e=0) should return E = M."""
        E = solve_kepler(0.0, 1.0)
        assert E == pytest.approx(1.0, abs=1e-10)

    def test_elliptical_orbit(self):
        """Test elliptical orbit with known solution."""
        e = 0.5
        M = 1.0
        E = solve_kepler(e, M)
        # Verify M = E - e*sin(E)
        M_check = E - e * np.sin(E)
        assert M_check == pytest.approx(M, abs=1e-10)

    def test_high_eccentricity(self):
        """Test near-parabolic orbit."""
        e = 0.99
        M = 0.1
        E = solve_kepler(e, M)
        M_check = E - e * np.sin(E)
        assert M_check == pytest.approx(M, abs=1e-8)

    def test_zero_mean_anomaly(self):
        """M=0 should give E=0 for any eccentricity."""
        for e in [0.0, 0.1, 0.5, 0.9]:
            E = solve_kepler(e, 0.0)
            assert E == pytest.approx(0.0, abs=1e-12)


class TestKeplerianToStateVector:
    """Test Keplerian to state vector conversion."""

    def test_circular_equatorial(self):
        """Circular equatorial orbit at 1000 km altitude."""
        elements = OrbitalState(
            a=7378.137,  # 1000 km altitude
            e=0.0,
            i=0.0,
            raan=0.0,
            argp=0.0,
            nu=0.0,
        )
        sv = keplerian_to_state_vector(elements)

        # At nu=0, position should be at periapsis on +x axis
        assert sv.x == pytest.approx(7378.137, rel=1e-6)
        assert sv.y == pytest.approx(0.0, abs=1e-6)
        assert sv.z == pytest.approx(0.0, abs=1e-6)

        # Velocity should be in +y direction
        v_mag = np.sqrt(sv.vx**2 + sv.vy**2 + sv.vz**2)
        expected_v = np.sqrt(398600.4418 / 7378.137)
        assert v_mag == pytest.approx(expected_v, rel=1e-6)

    def test_inclined_orbit(self):
        """Test inclined orbit produces z-component."""
        elements = OrbitalState(
            a=7378.137,
            e=0.0,
            i=np.radians(51.6),  # ISS inclination
            raan=0.0,
            argp=0.0,
            nu=0.0,
        )
        sv = keplerian_to_state_vector(elements)
        # At nu=0, z should be 0 but vz should be non-zero
        assert sv.z == pytest.approx(0.0, abs=1e-6)
        assert sv.vz != pytest.approx(0.0, abs=1e-6)


class TestSolarFlux:
    """Test solar flux computation."""

    def test_at_1au(self):
        """At 1 AU, flux should equal solar constant."""
        flux = compute_solar_flux(AU_KM)
        assert flux == pytest.approx(SOLAR_CONSTANT, rel=1e-6)

    def test_at_earth_orbit(self):
        """At Earth distance, flux should be ~1361 W/m^2."""
        flux = compute_solar_flux(149597870.7)
        assert flux == pytest.approx(1361.0, rel=1e-3)

    def test_inverse_square_law(self):
        """Flux should follow inverse square law."""
        flux_1au = compute_solar_flux(AU_KM)
        flux_2au = compute_solar_flux(2 * AU_KM)
        assert flux_2au == pytest.approx(flux_1au / 4, rel=1e-6)


class TestEclipseState:
    """Test eclipse state computation."""

    def test_sunlit(self):
        """Spacecraft in full sunlight - Sun and SC on same side of Earth."""
        sc_pos = np.array([7000.0, 0.0, 0.0])
        earth_pos = np.array([0.0, 0.0, 0.0])
        sun_pos = np.array([AU_KM, 0.0, 0.0])  # Sun in +x direction

        state, fraction = compute_eclipse_state(sc_pos, earth_pos, sun_pos)
        assert state == "SUNLIT"
        assert fraction == pytest.approx(0.0, abs=1e-6)

    def test_umbra(self):
        """Spacecraft in Earth's umbra - Earth between Sun and SC."""
        sc_pos = np.array([-7000.0, 0.0, 0.0])  # Behind Earth
        earth_pos = np.array([0.0, 0.0, 0.0])
        sun_pos = np.array([AU_KM, 0.0, 0.0])  # Sun in +x direction

        state, fraction = compute_eclipse_state(sc_pos, earth_pos, sun_pos)
        assert state == "UMBRA"
        assert fraction == pytest.approx(1.0, abs=1e-3)

    def test_penumbra(self):
        """Spacecraft in penumbra (partial shadow).

        Geometry: Sun along +x, spacecraft at ~300,000 km with 6,000 km offset
        so Earth's disk partially covers the Sun's disk.
        At this distance: Earth angular radius ~1.22 deg, Sun ~0.27 deg.
        Umbra cone boundary at ~0.95 deg, penumbra at ~1.48 deg.
        Theta = 1.14 deg falls in penumbra.
        """
        sc_pos = np.array([-300000.0, 6000.0, 0.0])
        earth_pos = np.array([0.0, 0.0, 0.0])
        sun_pos = np.array([AU_KM, 0.0, 0.0])

        state, fraction = compute_eclipse_state(sc_pos, earth_pos, sun_pos)
        assert state == "PENUMBRA"
        assert 0.0 < fraction < 1.0


class TestDSNVisibility:
    """Test DSN visibility computation."""

    def test_visible_site(self):
        """Site with spacecraft above horizon."""
        sc_pos = np.array([0.0, 0.0, 40000.0])  # High over north pole
        dsn_sites = {"TEST": np.array([0.0, 0.0, 6378.0])}  # Near north pole

        vis = compute_dsn_visibility(sc_pos, dsn_sites)
        assert vis["TEST"] is True or vis["TEST"] == np.True_

    def test_not_visible_site(self):
        """Site with spacecraft below horizon."""
        sc_pos = np.array([0.0, 0.0, -40000.0])  # Over south pole
        dsn_sites = {"TEST": np.array([0.0, 0.0, 6378.0])}  # North pole site

        vis = compute_dsn_visibility(sc_pos, dsn_sites)
        assert vis["TEST"] is False or vis["TEST"] == np.False_


class TestLightTime:
    """Test light time computation."""

    def test_earth_to_moon(self):
        """Light time Earth to Moon ~1.28s."""
        sc_pos = np.array([384400.0, 0.0, 0.0])
        earth_pos = np.array([0.0, 0.0, 0.0])

        lt = compute_light_time(sc_pos, earth_pos)
        assert lt == pytest.approx(1.28, abs=0.02)


class TestTwoBodyPropagation:
    """Test two-body orbit propagation."""

    def test_circular_orbit_propagation(self):
        """Circular orbit should maintain radius."""
        from physics_models.state_engine.physics import EARTH_MU, StateVector

        radius = 7000.0
        v = np.sqrt(EARTH_MU / radius)
        initial = StateVector(
            x=radius, y=0.0, z=0.0,
            vx=0.0, vy=v, vz=0.0,
            epoch=datetime.now(UTC)
        )

        # Propagate 1/4 orbit
        period = 2 * np.pi * np.sqrt(radius**3 / EARTH_MU)
        propagated = propagate_orbit_two_body(initial, period / 4)

        # Should be at y=radius
        new_radius = np.sqrt(propagated.x**2 + propagated.y**2 + propagated.z**2)
        assert new_radius == pytest.approx(radius, rel=1e-3)
        assert propagated.x == pytest.approx(0.0, abs=radius * 1e-3)


class TestAttitudeQuaternion:
    """Test attitude quaternion computation."""

    def test_default_returns_identity(self):
        """Default attitude should be identity quaternion."""
        from physics_models.state_engine.planned_attitude import AttitudeMode
        qw, qx, qy, qz = compute_attitude_quaternion(AttitudeMode.BIAS_NEG_XSI, timedelta(0))
        assert qw == pytest.approx(1.0)
        assert qx == pytest.approx(0.0)
        assert qy == pytest.approx(0.0)
        assert qz == pytest.approx(0.0)


class TestQuaternionToEuler:
    """Test quaternion to Euler conversion."""

    def test_identity_quaternion(self):
        """Identity quaternion should give zero Euler angles."""
        roll, pitch, yaw = quaternion_to_euler(1.0, 0.0, 0.0, 0.0)
        assert roll == pytest.approx(0.0, abs=1e-6)
        assert pitch == pytest.approx(0.0, abs=1e-6)
        assert yaw == pytest.approx(0.0, abs=1e-6)

    def test_90_deg_roll(self):
        """90 degree roll quaternion."""
        # q = [cos(45), sin(45), 0, 0] for 90 deg roll
        roll, pitch, yaw = quaternion_to_euler(np.sqrt(2)/2, np.sqrt(2)/2, 0.0, 0.0)
        assert roll == pytest.approx(90.0, abs=1e-3)
        assert pitch == pytest.approx(0.0, abs=1e-6)
        assert yaw == pytest.approx(0.0, abs=1e-6)


class TestSolarArrayPower:
    """Test solar array power computation."""

    def test_normal_incidence(self):
        """Normal incidence gives max power."""
        power = compute_solar_array_power(
            solar_flux=1361.0,
            incidence_angle_deg=0.0,
        )
        expected = 1361.0 * 44.8 * 0.28
        assert power == pytest.approx(expected, rel=1e-6)

    def test_90_deg_incidence(self):
        """90 deg incidence gives zero power."""
        power = compute_solar_array_power(
            solar_flux=1361.0,
            incidence_angle_deg=90.0,
        )
        assert power == pytest.approx(0.0, abs=1e-6)

    def test_degradation_factor(self):
        """Degradation factor reduces power linearly."""
        power_nominal = compute_solar_array_power(1361.0, 0.0, degradation_factor=1.0)
        power_degraded = compute_solar_array_power(1361.0, 0.0, degradation_factor=0.8)
        assert power_degraded == pytest.approx(power_nominal * 0.8, rel=1e-6)

    def test_temperature_derating(self):
        """High temperature reduces power."""
        power_cold = compute_solar_array_power(1361.0, 0.0, temperature_k=273.15)  # 0C
        power_hot = compute_solar_array_power(1361.0, 0.0, temperature_k=353.15)  # 80C
        assert power_hot < power_cold


class TestStateEnginePhysics:
    """Test StateEnginePhysics class."""

    @pytest.fixture
    def physics(self):
        liftoff = datetime(2026, 4, 1, 22, 35, 0, tzinfo=UTC)
        return StateEnginePhysics(liftoff)

    def test_compute_state_at_met_returns_all_fields(self, physics):
        """State dict should contain all required fields."""
        met = timedelta(hours=1)
        state = physics.compute_state_at_met(met)

        required_fields = [
            "timestamp_utc", "x_km", "y_km", "z_km",
            "vx_kms", "vy_kms", "vz_kms",
            "distance_from_sun_au", "solar_flux_w_m2",
            "solar_incidence_angle_deg", "eclipse_state",
            "eclipse_fraction", "earth_distance_km",
            "dsn_visibility", "light_time_s",
            "solar_array_angle_deg", "roll_deg", "pitch_deg", "yaw_deg",
            "attitude_mode",
        ]
        for field in required_fields:
            assert field in state, f"Missing field: {field}"

    def test_timestamp_matches_met(self, physics):
        """Timestamp should equal liftoff + MET."""
        met = timedelta(hours=2, minutes=30)
        state = physics.compute_state_at_met(met)
        expected = physics.liftoff_utc + met
        assert state["timestamp_utc"] == expected

    def test_solar_flux_reasonable(self, physics):
        """Solar flux should be near Earth value."""
        state = physics.compute_state_at_met(timedelta(hours=1))
        # Near Earth, should be ~1361 W/m^2
        assert 1300 < state["solar_flux_w_m2"] < 1450

    def test_earth_distance_reasonable(self, physics):
        """Earth distance should be near orbital radius."""
        state = physics.compute_state_at_met(timedelta(hours=1))
        # LEO altitude ~300 km -> radius ~6678 km
        assert 6000 < state["earth_distance_km"] < 8000

    def test_light_time_reasonable(self, physics):
        """Light time should be reasonable for LEO."""
        state = physics.compute_state_at_met(timedelta(hours=1))
        # LEO light time < 0.1s
        assert 0 <= state["light_time_s"] < 1.0

    def test_attitude_mode_from_planned(self, physics):
        """Attitude mode should come from planned_attitude resolver."""
        state = physics.compute_state_at_met(timedelta(hours=1))
        assert state["attitude_mode"] in [m.value for m in __import__(
            'physics_models.state_engine.planned_attitude', fromlist=['AttitudeMode']
        ).AttitudeMode]


class TestPlannedAttitudeIntegration:
    """Test integration with planned_attitude module."""

    def test_resolve_attitude_returns_mode_and_def(self):
        from physics_models.state_engine.planned_attitude import resolve_attitude
        mode, mode_def = resolve_attitude(timedelta(hours=1))
        assert mode is not None
        assert mode_def is not None
        assert "description" in mode_def

    def test_solar_incidence_angle_estimate(self):
        from physics_models.state_engine.planned_attitude import (
            get_solar_incidence_angle_estimate,
        )
        angle = get_solar_incidence_angle_estimate(timedelta(hours=1))
        assert 0 <= angle <= 180

    def test_solar_array_gimbal_estimate(self):
        from physics_models.state_engine.planned_attitude import (
            get_solar_array_gimbal_estimate,
        )
        angle = get_solar_array_gimbal_estimate(timedelta(hours=1))
        assert -180 <= angle <= 180