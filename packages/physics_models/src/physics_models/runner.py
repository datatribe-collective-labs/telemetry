"""SimulatorRunner — orchestrates all physics model generators at tick rate."""

import asyncio
import os
import signal
import time
from datetime import UTC, datetime, timedelta

from contracts import (
    SyntheticAnomalyEvent,
    SyntheticCommsOutput,
    SyntheticMLFeatureVector,
    SyntheticPowerOutput,
    SyntheticRadiationOutput,
    SyntheticStateSnapshot,
    SyntheticTelemetryPacket,
    SyntheticThermalOutput,
)
from contracts.planned_attitude import (
    get_solar_array_gimbal_estimate,
    get_solar_incidence_angle_estimate,
)

from physics_models.config import PhysicsModelsConfig, load_config
from physics_models.cross_model import CrossModelBus
from physics_models.kafka import PhysicsModelsKafkaProducer
from physics_models.oem import (
    OemEphemeris,
    interpolate_state,
    load_latest_oem_from_store,
    load_oem_asc,
)
from physics_models.power.physics import PowerModel
from physics_models.state_engine.physics import (
    compute_eclipse_state,
    compute_solar_flux,
)
from physics_models.thermal.physics import ThermalModel3Node


class SimulatorRunner:
    """Orchestrates all physics model generators at configured tick rate."""

    def __init__(self, config: PhysicsModelsConfig):
        self.config = config
        self.tick_interval = 1.0 / config.tick_hz
        self.running = False
        self._tick_count = 0

        # Initialize Kafka producer
        self.producer = PhysicsModelsKafkaProducer(config.kafka.bootstrap_servers)

        # Initialize cross-model bus
        self.cross_model = CrossModelBus()

        # Parse liftoff time
        self.liftoff_utc = datetime.fromisoformat(config.state_engine.liftoff_utc)

        # State
        self._start_time: datetime | None = None

        # Signal handling moved to run() to avoid issues with asyncio event loop
        # in Docker environments. Use asyncio signal handlers inside run().
        self._signal_handlers_installed = False

        # Owned physics models (state / thermal / power are wired; comms,
        # radiation, anomaly and ML remain placeholders owned by others).
        self.oem_ephemeris: OemEphemeris | None = self._load_oem(config)
        self.thermal_model = ThermalModel3Node.from_config(config.thermal.model_dump())
        self.power_model = PowerModel()
        self.base_load_w = 1200.0  # placeholder load profile (Orion EPS budget TBD)

    def _load_oem(self, config: PhysicsModelsConfig) -> OemEphemeris | None:
        """Load NASA OEM ephemeris per config; None means placeholder orbit mode."""
        se = config.state_engine
        try:
            if se.oem_source == "oem_file" and se.oem_file_path:
                eph = load_oem_asc(se.oem_file_path)
            elif se.oem_source == "oem_store" and se.oem_store_path:
                eph = load_latest_oem_from_store(se.oem_store_path)
            else:
                return None
        except (OSError, ValueError) as exc:
            print(f"WARNING: OEM load failed ({exc}); falling back to placeholder orbit")
            return None
        print(
            f"Loaded OEM arc '{eph.object_name}' ({eph.center_name}/{eph.ref_frame}): "
            f"{eph.start.isoformat()} → {eph.stop.isoformat()}"
        )
        return eph

    def _approx_sun_position(self, t: datetime):
        """Rough Sun position at ~1 AU (circular ecliptic approximation).

        Accuracy is sufficient for solar flux (~±1%) and the eclipse geometry in
        this simulation. Replace with a JPL ephemeris source if higher fidelity
        is required.
        """
        import numpy as np

        sun_omega = 2 * np.pi / (365.25 * 86400)
        theta = sun_omega * t.timestamp()
        from physics_models.state_engine.physics import AU_KM

        return np.array([AU_KM * np.cos(theta), AU_KM * np.sin(theta), 0.0])

    def _signal_handler(self, signum=None, frame=None):
        print(f"\nReceived signal {signum}, shutting down...")
        self.running = False

    def _install_signal_handlers(self):
        """Install asyncio-compatible signal handlers. Call from inside run()."""
        if self._signal_handlers_installed:
            return
        try:
            loop = asyncio.get_running_loop()
            for sig in (signal.SIGINT, signal.SIGTERM):
                loop.add_signal_handler(sig, self._signal_handler)
            self._signal_handlers_installed = True
        except (NotImplementedError, RuntimeError):
            # Not available on Windows or if no running loop
            pass

    async def run(self) -> None:
        """Main simulation loop."""
        # Install signal handlers now that we're in an async context
        self._install_signal_handlers()

        self.running = True
        self._start_time = datetime.now(UTC)

        print(f"Starting physics models simulation at {self.config.tick_hz} Hz")
        print(f"Liftoff: {self.liftoff_utc.isoformat()}")
        print(f"Kafka: {self.config.kafka.bootstrap_servers}")

        while self.running:
            tick_start = time.perf_counter()

            # Current simulation time: replay the mission from (liftoff + start_met_seconds),
            # at time_scale × real speed (tick pacing stays 1 Hz on the wall clock).
            sim_seconds = (
                self.config.start_met_seconds
                + (self._tick_count / self.config.tick_hz) * self.config.time_scale
            )
            current_tick = self.liftoff_utc + timedelta(seconds=sim_seconds)
            met = current_tick - self.liftoff_utc

            # 1. State Engine (authoritative state)
            state = self._tick_state_engine(current_tick, met)
            self._last_state = state  # consumed by thermal/power ticks below

            # 2. Physics models (parallelizable in future)
            thermal = self._tick_thermal(current_tick, met)
            power = self._tick_power(current_tick, met)
            comms = self._tick_comms(current_tick, met)
            radiation = self._tick_radiation(current_tick, met)

            # 3. Cross-model bus update (for next tick)
            self.cross_model.update(thermal, power, comms, radiation)

            # 4. Telemetry packet assembly
            packet = self._assemble_packet(state, thermal, power, comms, radiation)

            # 5. Anomaly detection
            anomaly = self._check_anomaly(packet)

            # 6. ML feature vector
            ml_features = self._build_ml_features(packet)

            # 7. Send to Kafka
            self._send_to_kafka(state, thermal, power, comms, radiation, packet, anomaly, ml_features)

            self._tick_count += 1

            # Tick pacing
            elapsed = time.perf_counter() - tick_start
            sleep_time = max(0, self.tick_interval - elapsed)
            if sleep_time > 0:
                await asyncio.sleep(sleep_time)
            elif elapsed > self.tick_interval:
                print(f"WARNING: Tick {self._tick_count} took {elapsed:.3f}s (budget: {self.tick_interval:.3f}s)")

        # Flush on shutdown
        self.producer.flush()
        print(f"Simulation stopped after {self._tick_count} ticks")

    def _tick_state_engine(self, current_tick: datetime, met: timedelta) -> SyntheticStateSnapshot:
        """State engine tick - authoritative spacecraft state from NASA OEM arcs."""
        import numpy as np

        # Solar angles from planned attitude timeline
        solar_incidence = get_solar_incidence_angle_estimate(met)
        solar_array_gimbal = get_solar_array_gimbal_estimate(met)

        sun_pos = self._approx_sun_position(current_tick)
        earth_pos = np.zeros(3)

        if self.oem_ephemeris is not None:
            sc_pos, sc_vel = interpolate_state(self.oem_ephemeris, current_tick)
        else:
            # Fallback placeholder: 300 km circular equatorial orbit
            from math import cos, sin, sqrt

            radius = 6378.137 + 300.0
            velocity = sqrt(398600.4418 / radius)
            theta = velocity / radius * met.total_seconds()
            sc_pos = np.array([radius * cos(theta), radius * sin(theta), 0.0])
            sc_vel = np.array([-velocity * sin(theta), velocity * cos(theta), 0.0])

        r_sc_sun = float(np.linalg.norm(sun_pos - sc_pos))
        eclipse_state, eclipse_fraction = compute_eclipse_state(sc_pos, earth_pos, sun_pos)
        earth_distance = float(np.linalg.norm(sc_pos))

        return SyntheticStateSnapshot(
            timestamp_utc=current_tick,
            x_km=float(sc_pos[0]), y_km=float(sc_pos[1]), z_km=float(sc_pos[2]),
            vx_kms=float(sc_vel[0]), vy_kms=float(sc_vel[1]), vz_kms=float(sc_vel[2]),
            distance_from_sun_au=r_sc_sun / 149597870.7,
            solar_flux_w_m2=compute_solar_flux(r_sc_sun),
            solar_incidence_angle_deg=solar_incidence,
            eclipse_state=eclipse_state,
            eclipse_fraction=eclipse_fraction,
            earth_distance_km=earth_distance,
            dsn_visibility=True,  # real per-site geometry comes from the pipelines
            light_time_s=earth_distance / 299792.458,
            solar_array_angle_deg=solar_array_gimbal,
            roll_deg=0.0,  # AROW attitude unavailable (contract: null/placeholder OK)
            pitch_deg=0.0,
            yaw_deg=0.0,
        )

    def _tick_thermal(self, current_tick: datetime, met: timedelta) -> SyntheticThermalOutput:
        """Thermal model tick - 3-node lumped parameter (ThermalModel3Node)."""
        state = self._last_state
        dt = self.config.time_scale / self.config.tick_hz  # sim-seconds per tick (time scaling)
        internal_heat_w = self.config.thermal.bay_heat_fraction * self.cross_model.power_dissipation_w

        self.thermal_model.step(
            solar_flux=state.solar_flux_w_m2,
            solar_incidence_angle_deg=state.solar_incidence_angle_deg,
            eclipse_fraction=state.eclipse_fraction,
            internal_power_w=internal_heat_w,
            dt=dt,
        )
        flows = self.thermal_model.get_heat_flows(
            state.solar_flux_w_m2,
            state.solar_incidence_angle_deg,
            state.eclipse_fraction,
        )
        q_rad_total = max(0.0, flows["q_rad_sun_w"] + flows["q_rad_shadow_w"] + flows["q_rad_elec_w"])

        return SyntheticThermalOutput(
            timestamp_utc=current_tick,
            temp_sun_face_k=self.thermal_model.T_sun_face_k,
            temp_shadow_face_k=self.thermal_model.T_shadow_face_k,
            temp_electronics_bay_k=self.thermal_model.T_electronics_bay_k,
            q_solar_absorbed_w=flows["q_solar_absorbed_w"],
            q_radiated_w=q_rad_total,
            q_internal_w=internal_heat_w,
            heater_active=self.thermal_model.heater_active,
            heater_power_w=flows["q_heater_w"],
            thermal_state=self.thermal_model.thermal_state(),
        )

    def _tick_power(self, current_tick: datetime, met: timedelta) -> SyntheticPowerOutput:
        """Power model tick - solar array, battery, loads (PowerModel)."""
        state = self._last_state
        dt = self.config.time_scale / self.config.tick_hz  # sim-seconds per tick (time scaling)
        total_load = self.base_load_w + (self.thermal_model.heater_power_w if self.thermal_model.heater_active else 0.0)

        self.power_model.step(
            solar_flux=state.solar_flux_w_m2,
            incidence_angle_deg=state.solar_array_angle_deg,
            eclipse_fraction=state.eclipse_fraction,
            total_load_w=total_load,
            dt=dt,
            electronics_bay_temp_k=self.cross_model.electronics_bay_temp_k,
            degradation_factor=self.cross_model.solar_array_degradation_factor,
        )
        ps = self.power_model.get_state()

        return SyntheticPowerOutput(
            timestamp_utc=current_tick,
            solar_array_power_w=ps["array_power_w"],
            array_efficiency=self.power_model.array_efficiency,
            total_load_w=ps["total_load_w"],
            battery_soc_pct=ps["battery_soc_pct"],
            battery_voltage_v=ps["battery_voltage_v"],
            battery_current_a=ps["battery_current_a"],
            net_power_w=ps["net_power_w"],
            available_power_w=ps["available_power_w"],
            power_state=ps["power_state"],
        )

    def _tick_comms(self, current_tick: datetime, met: timedelta) -> SyntheticCommsOutput:
        """Comms model tick - S-band link budget."""
        # TODO: Implement S-band link budget
        # Uses cross_model.plasma_noise_factor
        return SyntheticCommsOutput(
            timestamp_utc=current_tick,
            eirp_dbw=20.0,
            free_space_path_loss_db=200.0,
            received_power_dbw=-180.0,
            eb_n0_db=10.0,
            link_margin_db=5.0,
            data_rate_kbps=128.0,
            signal_quality=0.95,
            comm_state="NOMINAL",
        )

    def _tick_radiation(self, current_tick: datetime, met: timedelta) -> SyntheticRadiationOutput:
        """Radiation model tick - AP-8/AE-8 dose."""
        # TODO: Implement radiation model
        # Outputs feed cross_model: solar_array_degradation, thermal_coating_*_factor, plasma_noise_factor
        return SyntheticRadiationOutput(
            timestamp_utc=current_tick,
            total_dose_rate_rad_s=0.001,
            cumulative_dose_krad=0.0,
            solar_array_degradation=1.0,
            thermal_alpha_degradation=1.0,
            thermal_eps_degradation=1.0,
            radiation_dose_rate_mrad_hr=0.1,
            sep_event_active=False,
        )

    def _assemble_packet(
        self,
        state: SyntheticStateSnapshot,
        thermal: SyntheticThermalOutput,
        power: SyntheticPowerOutput,
        comms: SyntheticCommsOutput,
        radiation: SyntheticRadiationOutput,
    ) -> SyntheticTelemetryPacket:
        """Assemble combined telemetry packet."""
        # All nominal if all subsystems nominal
        all_nominal = (
            thermal.thermal_state == "NOMINAL" and
            power.power_state == "NOMINAL" and
            comms.comm_state == "NOMINAL"
        )

        return SyntheticTelemetryPacket(
            timestamp_utc=state.timestamp_utc,
            spacecraft_id="ORION_EM2",
            # Thermal
            temp_sun_face_k=thermal.temp_sun_face_k,
            temp_shadow_face_k=thermal.temp_shadow_face_k,
            temp_electronics_bay_k=thermal.temp_electronics_bay_k,
            heater_active=thermal.heater_active,
            thermal_state=thermal.thermal_state,
            # Power
            battery_voltage_v=power.battery_voltage_v,
            battery_soc_pct=power.battery_soc_pct,
            solar_array_power_w=power.solar_array_power_w,
            power_state=power.power_state,
            # Comms
            signal_quality=comms.signal_quality,
            link_margin_db=comms.link_margin_db,
            data_rate_kbps=comms.data_rate_kbps,
            comm_state=comms.comm_state,
            # Radiation
            radiation_dose_rate_mrad_hr=radiation.radiation_dose_rate_mrad_hr,
            cumulative_dose_krad=radiation.cumulative_dose_krad,
            sep_event_active=radiation.sep_event_active,
            # Derived
            all_nominal=all_nominal,
        )

    def _check_anomaly(self, packet: SyntheticTelemetryPacket) -> SyntheticAnomalyEvent | None:
        """Anomaly detection - placeholder."""
        # TODO: Implement 2-layer detection + ML
        return None

    def _build_ml_features(self, packet: SyntheticTelemetryPacket) -> SyntheticMLFeatureVector:
        """ML feature vector builder - placeholder."""
        # TODO: Implement feature extraction
        return SyntheticMLFeatureVector(
            timestamp_utc=packet.timestamp_utc,
            temp_elec_norm=0.5,
            temp_sun_norm=0.5,
            temp_shadow_norm=0.5,
            soc_norm=0.9,
            voltage_norm=0.9,
            signal_quality=packet.signal_quality,
            dose_rate_norm=0.0,
            r_re_norm=0.5,
            earth_dist_norm=0.5,
            eclipse_fraction=0.0,
            in_belt=0.0,
            sep_active=0.0,
            dsn_visible=1.0,
            temp_sun_residual_k=0.0,
            link_margin_residual_db=0.0,
            array_efficiency_ratio=1.0,
            voltage_residual_v=0.0,
            dose_rate_ratio=1.0,
            temp_elec_rate_k_min=0.0,
            soc_rate_pct_hr=0.0,
            dose_rate_delta_mrad_hr=0.0,
            signal_quality_delta=0.0,
        )

    def _send_to_kafka(
        self,
        state: SyntheticStateSnapshot,
        thermal: SyntheticThermalOutput,
        power: SyntheticPowerOutput,
        comms: SyntheticCommsOutput,
        radiation: SyntheticRadiationOutput,
        packet: SyntheticTelemetryPacket,
        anomaly: SyntheticAnomalyEvent | None,
        ml_features: SyntheticMLFeatureVector,
    ) -> None:
        """Send all outputs to Kafka."""
        self.producer.send_state(state)
        self.producer.send_thermal(thermal)
        self.producer.send_power(power)
        self.producer.send_comms(comms)
        self.producer.send_radiation(radiation)
        self.producer.send_cross_model(self.cross_model.to_cross_model_state(state.timestamp_utc))
        self.producer.send_packet(packet)
        if anomaly:
            self.producer.send_anomaly(anomaly)
        self.producer.send_ml_features(ml_features)
        self.producer.poll(0.0)  # Non-blocking poll for delivery callbacks


async def main():
    """Entry point for running the simulator."""

    config_path = os.environ.get("PHYSICS_MODELS_CONFIG", "configs/default.yaml")
    config = load_config(config_path)

    # Demo controls: replay speed and seek (wall-clock 1 Hz ticks are unchanged).
    if scale := os.environ.get("PHYSICS_MODELS_TIME_SCALE"):
        config.time_scale = float(scale)
    if seek := os.environ.get("PHYSICS_MODELS_START_MET_SECONDS"):
        config.start_met_seconds = float(seek)

    runner = SimulatorRunner(config)
    await runner.run()


if __name__ == "__main__":
    asyncio.run(main())