"""Kafka consumer for physics models — writes synthetic telemetry to TimescaleDB."""

import json
import os
import signal

from confluent_kafka import Consumer, KafkaError
from contracts import (
    SyntheticAnomalyEvent,
    SyntheticCommsOutput,
    SyntheticCrossModelState,
    SyntheticMLFeatureVector,
    SyntheticPowerOutput,
    SyntheticRadiationOutput,
    SyntheticStateSnapshot,
    SyntheticTelemetryPacket,
    SyntheticThermalOutput,
)
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

# Database setup - REQUIRED env vars, no defaults
DATABASE_URL = os.environ["DATABASE_URL"]
engine = create_engine(DATABASE_URL, pool_pre_ping=True)
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)

# Kafka consumer config - REQUIRED env var
KAFKA_BOOTSTRAP = os.environ["KAFKA_BOOTSTRAP_SERVERS"]
CONSUMER_CONFIG = {
    "bootstrap.servers": KAFKA_BOOTSTRAP,
    "group.id": "physics_models_consumer",
    "auto.offset.reset": "earliest",
    "enable.auto.commit": True,
    "auto.commit.interval.ms": 5000,
}

TOPICS = [
    "trajectory",
    "telemetry",
    "cross_model_state",
    "events",
    "ml_features",
]

# Type discriminators in telemetry topic
# Order matters: check for packet first (has all fields), then specific types
TYPE_FIELD_MAP = {
    "spacecraft_id": "telemetry_packet",
    "temp_sun_face_k": "thermal_output",
    "solar_array_power_w": "power_output",
    "eirp_dbw": "comms_output",
    "total_dose_rate_rad_s": "radiation_output",
}


class TelemetryConsumer:
    """Consumes physics model outputs from Kafka and writes to TimescaleDB."""

    def __init__(self):
        self.consumer = Consumer(CONSUMER_CONFIG)
        self.running = False
        self._setup_signal_handlers()

    def _setup_signal_handlers(self):
        signal.signal(signal.SIGINT, self._signal_handler)
        signal.signal(signal.SIGTERM, self._signal_handler)

    def _signal_handler(self, signum, frame):
        print(f"\nReceived signal {signum}, shutting down...")
        self.running = False

    def _get_telemetry_table(self, payload: dict) -> str | None:
        """Determine which table a telemetry message belongs to."""
        for key, table in TYPE_FIELD_MAP.items():
            if key in payload:
                return table
        return None

    def _insert_state(self, session, msg: SyntheticStateSnapshot):
        session.execute(text("""
            INSERT INTO state_snapshot (
                timestamp_utc, x_km, y_km, z_km, vx_kms, vy_kms, vz_kms,
                distance_from_sun_au, solar_flux_w_m2, solar_incidence_angle_deg,
                eclipse_state, eclipse_fraction, earth_distance_km,
                dsn_visibility, light_time_s, solar_array_angle_deg,
                roll_deg, pitch_deg, yaw_deg
            ) VALUES (
                :timestamp_utc, :x_km, :y_km, :z_km, :vx_kms, :vy_kms, :vz_kms,
                :distance_from_sun_au, :solar_flux_w_m2, :solar_incidence_angle_deg,
                :eclipse_state, :eclipse_fraction, :earth_distance_km,
                :dsn_visibility, :light_time_s, :solar_array_angle_deg,
                :roll_deg, :pitch_deg, :yaw_deg
            )
            ON CONFLICT (timestamp_utc) DO UPDATE SET
                x_km = EXCLUDED.x_km, y_km = EXCLUDED.y_km, z_km = EXCLUDED.z_km,
                vx_kms = EXCLUDED.vx_kms, vy_kms = EXCLUDED.vy_kms, vz_kms = EXCLUDED.vz_kms,
                distance_from_sun_au = EXCLUDED.distance_from_sun_au,
                solar_flux_w_m2 = EXCLUDED.solar_flux_w_m2,
                solar_incidence_angle_deg = EXCLUDED.solar_incidence_angle_deg,
                eclipse_state = EXCLUDED.eclipse_state,
                eclipse_fraction = EXCLUDED.eclipse_fraction,
                earth_distance_km = EXCLUDED.earth_distance_km,
                dsn_visibility = EXCLUDED.dsn_visibility,
                light_time_s = EXCLUDED.light_time_s,
                solar_array_angle_deg = EXCLUDED.solar_array_angle_deg,
                roll_deg = EXCLUDED.roll_deg, pitch_deg = EXCLUDED.pitch_deg, yaw_deg = EXCLUDED.yaw_deg
        """), msg.model_dump())

    def _insert_thermal(self, session, msg: SyntheticThermalOutput):
        session.execute(text("""
            INSERT INTO thermal_output (
                timestamp_utc, temp_sun_face_k, temp_shadow_face_k,
                temp_electronics_bay_k, q_solar_absorbed_w, q_radiated_w,
                q_internal_w, heater_active, heater_power_w, thermal_state
            ) VALUES (
                :timestamp_utc, :temp_sun_face_k, :temp_shadow_face_k,
                :temp_electronics_bay_k, :q_solar_absorbed_w, :q_radiated_w,
                :q_internal_w, :heater_active, :heater_power_w, :thermal_state
            )
            ON CONFLICT (timestamp_utc) DO UPDATE SET
                temp_sun_face_k = EXCLUDED.temp_sun_face_k,
                temp_shadow_face_k = EXCLUDED.temp_shadow_face_k,
                temp_electronics_bay_k = EXCLUDED.temp_electronics_bay_k,
                q_solar_absorbed_w = EXCLUDED.q_solar_absorbed_w,
                q_radiated_w = EXCLUDED.q_radiated_w,
                q_internal_w = EXCLUDED.q_internal_w,
                heater_active = EXCLUDED.heater_active,
                heater_power_w = EXCLUDED.heater_power_w,
                thermal_state = EXCLUDED.thermal_state
        """), msg.model_dump())

    def _insert_power(self, session, msg: SyntheticPowerOutput):
        session.execute(text("""
            INSERT INTO power_output (
                timestamp_utc, solar_array_power_w, array_efficiency,
                total_load_w, battery_soc_pct, battery_voltage_v,
                battery_current_a, net_power_w, available_power_w, power_state
            ) VALUES (
                :timestamp_utc, :solar_array_power_w, :array_efficiency,
                :total_load_w, :battery_soc_pct, :battery_voltage_v,
                :battery_current_a, :net_power_w, :available_power_w, :power_state
            )
            ON CONFLICT (timestamp_utc) DO UPDATE SET
                solar_array_power_w = EXCLUDED.solar_array_power_w,
                array_efficiency = EXCLUDED.array_efficiency,
                total_load_w = EXCLUDED.total_load_w,
                battery_soc_pct = EXCLUDED.battery_soc_pct,
                battery_voltage_v = EXCLUDED.battery_voltage_v,
                battery_current_a = EXCLUDED.battery_current_a,
                net_power_w = EXCLUDED.net_power_w,
                available_power_w = EXCLUDED.available_power_w,
                power_state = EXCLUDED.power_state
        """), msg.model_dump())

    def _insert_comms(self, session, msg: SyntheticCommsOutput):
        session.execute(text("""
            INSERT INTO comms_output (
                timestamp_utc, eirp_dbw, free_space_path_loss_db,
                received_power_dbw, eb_n0_db, link_margin_db,
                data_rate_kbps, signal_quality, comm_state
            ) VALUES (
                :timestamp_utc, :eirp_dbw, :free_space_path_loss_db,
                :received_power_dbw, :eb_n0_db, :link_margin_db,
                :data_rate_kbps, :signal_quality, :comm_state
            )
            ON CONFLICT (timestamp_utc) DO UPDATE SET
                eirp_dbw = EXCLUDED.eirp_dbw,
                free_space_path_loss_db = EXCLUDED.free_space_path_loss_db,
                received_power_dbw = EXCLUDED.received_power_dbw,
                eb_n0_db = EXCLUDED.eb_n0_db,
                link_margin_db = EXCLUDED.link_margin_db,
                data_rate_kbps = EXCLUDED.data_rate_kbps,
                signal_quality = EXCLUDED.signal_quality,
                comm_state = EXCLUDED.comm_state
        """), msg.model_dump())

    def _insert_radiation(self, session, msg: SyntheticRadiationOutput):
        session.execute(text("""
            INSERT INTO radiation_output (
                timestamp_utc, total_dose_rate_rad_s, cumulative_dose_krad,
                solar_array_degradation, thermal_alpha_degradation,
                thermal_eps_degradation, radiation_dose_rate_mrad_hr,
                sep_event_active
            ) VALUES (
                :timestamp_utc, :total_dose_rate_rad_s, :cumulative_dose_krad,
                :solar_array_degradation, :thermal_alpha_degradation,
                :thermal_eps_degradation, :radiation_dose_rate_mrad_hr,
                :sep_event_active
            )
            ON CONFLICT (timestamp_utc) DO UPDATE SET
                total_dose_rate_rad_s = EXCLUDED.total_dose_rate_rad_s,
                cumulative_dose_krad = EXCLUDED.cumulative_dose_krad,
                solar_array_degradation = EXCLUDED.solar_array_degradation,
                thermal_alpha_degradation = EXCLUDED.thermal_alpha_degradation,
                thermal_eps_degradation = EXCLUDED.thermal_eps_degradation,
                radiation_dose_rate_mrad_hr = EXCLUDED.radiation_dose_rate_mrad_hr,
                sep_event_active = EXCLUDED.sep_event_active
        """), msg.model_dump())

    def _insert_packet(self, session, msg: SyntheticTelemetryPacket):
        session.execute(text("""
            INSERT INTO telemetry_packet (
                timestamp_utc, spacecraft_id,
                temp_sun_face_k, temp_shadow_face_k, temp_electronics_bay_k,
                heater_active, thermal_state,
                battery_voltage_v, battery_soc_pct, solar_array_power_w, power_state,
                signal_quality, link_margin_db, data_rate_kbps, comm_state,
                radiation_dose_rate_mrad_hr, cumulative_dose_krad, sep_event_active,
                all_nominal
            ) VALUES (
                :timestamp_utc, :spacecraft_id,
                :temp_sun_face_k, :temp_shadow_face_k, :temp_electronics_bay_k,
                :heater_active, :thermal_state,
                :battery_voltage_v, :battery_soc_pct, :solar_array_power_w, :power_state,
                :signal_quality, :link_margin_db, :data_rate_kbps, :comm_state,
                :radiation_dose_rate_mrad_hr, :cumulative_dose_krad, :sep_event_active,
                :all_nominal
            )
            ON CONFLICT (timestamp_utc) DO UPDATE SET
                spacecraft_id = EXCLUDED.spacecraft_id,
                temp_sun_face_k = EXCLUDED.temp_sun_face_k,
                temp_shadow_face_k = EXCLUDED.temp_shadow_face_k,
                temp_electronics_bay_k = EXCLUDED.temp_electronics_bay_k,
                heater_active = EXCLUDED.heater_active,
                thermal_state = EXCLUDED.thermal_state,
                battery_voltage_v = EXCLUDED.battery_voltage_v,
                battery_soc_pct = EXCLUDED.battery_soc_pct,
                solar_array_power_w = EXCLUDED.solar_array_power_w,
                power_state = EXCLUDED.power_state,
                signal_quality = EXCLUDED.signal_quality,
                link_margin_db = EXCLUDED.link_margin_db,
                data_rate_kbps = EXCLUDED.data_rate_kbps,
                comm_state = EXCLUDED.comm_state,
                radiation_dose_rate_mrad_hr = EXCLUDED.radiation_dose_rate_mrad_hr,
                cumulative_dose_krad = EXCLUDED.cumulative_dose_krad,
                sep_event_active = EXCLUDED.sep_event_active,
                all_nominal = EXCLUDED.all_nominal
        """), msg.model_dump())

    def _insert_cross_model(self, session, msg: SyntheticCrossModelState):
        session.execute(text("""
            INSERT INTO cross_model_state (
                timestamp_utc, electronics_bay_temp_k, power_dissipation_w,
                available_power_w, solar_array_degradation_factor,
                thermal_coating_alpha_factor, thermal_coating_eps_factor,
                plasma_noise_factor
            ) VALUES (
                :timestamp_utc, :electronics_bay_temp_k, :power_dissipation_w,
                :available_power_w, :solar_array_degradation_factor,
                :thermal_coating_alpha_factor, :thermal_coating_eps_factor,
                :plasma_noise_factor
            )
            ON CONFLICT (timestamp_utc) DO UPDATE SET
                electronics_bay_temp_k = EXCLUDED.electronics_bay_temp_k,
                power_dissipation_w = EXCLUDED.power_dissipation_w,
                available_power_w = EXCLUDED.available_power_w,
                solar_array_degradation_factor = EXCLUDED.solar_array_degradation_factor,
                thermal_coating_alpha_factor = EXCLUDED.thermal_coating_alpha_factor,
                thermal_coating_eps_factor = EXCLUDED.thermal_coating_eps_factor,
                plasma_noise_factor = EXCLUDED.plasma_noise_factor
        """), msg.model_dump())

    def _insert_anomaly(self, session, msg: SyntheticAnomalyEvent):
        session.execute(text("""
            INSERT INTO anomaly_events (
                timestamp_utc, event_id, anomaly_type, severity,
                description, affected_subsystem, confidence_score,
                raw_features_json, detection_layer
            ) VALUES (
                :timestamp_utc, :event_id, :anomaly_type, :severity,
                :description, :affected_subsystem, :confidence_score,
                :raw_features_json, :detection_layer
            )
            ON CONFLICT (event_id) DO UPDATE SET
                timestamp_utc = EXCLUDED.timestamp_utc,
                anomaly_type = EXCLUDED.anomaly_type,
                severity = EXCLUDED.severity,
                description = EXCLUDED.description,
                affected_subsystem = EXCLUDED.affected_subsystem,
                confidence_score = EXCLUDED.confidence_score,
                raw_features_json = EXCLUDED.raw_features_json,
                detection_layer = EXCLUDED.detection_layer
        """), msg.model_dump())

    def _insert_ml_features(self, session, msg: SyntheticMLFeatureVector):
        session.execute(text("""
            INSERT INTO ml_feature_vectors (
                timestamp_utc,
                temp_elec_norm, temp_sun_norm, temp_shadow_norm,
                soc_norm, voltage_norm, signal_quality, dose_rate_norm,
                r_re_norm, earth_dist_norm, eclipse_fraction,
                in_belt, sep_active, dsn_visible,
                temp_sun_residual_k, link_margin_residual_db,
                array_efficiency_ratio, voltage_residual_v, dose_rate_ratio,
                temp_elec_rate_k_min, soc_rate_pct_hr,
                dose_rate_delta_mrad_hr, signal_quality_delta
            ) VALUES (
                :timestamp_utc,
                :temp_elec_norm, :temp_sun_norm, :temp_shadow_norm,
                :soc_norm, :voltage_norm, :signal_quality, :dose_rate_norm,
                :r_re_norm, :earth_dist_norm, :eclipse_fraction,
                :in_belt, :sep_active, :dsn_visible,
                :temp_sun_residual_k, :link_margin_residual_db,
                :array_efficiency_ratio, :voltage_residual_v, :dose_rate_ratio,
                :temp_elec_rate_k_min, :soc_rate_pct_hr,
                :dose_rate_delta_mrad_hr, :signal_quality_delta
            )
            ON CONFLICT (timestamp_utc) DO UPDATE SET
                temp_elec_norm = EXCLUDED.temp_elec_norm,
                temp_sun_norm = EXCLUDED.temp_sun_norm,
                temp_shadow_norm = EXCLUDED.temp_shadow_norm,
                soc_norm = EXCLUDED.soc_norm,
                voltage_norm = EXCLUDED.voltage_norm,
                signal_quality = EXCLUDED.signal_quality,
                dose_rate_norm = EXCLUDED.dose_rate_norm,
                r_re_norm = EXCLUDED.r_re_norm,
                earth_dist_norm = EXCLUDED.earth_dist_norm,
                eclipse_fraction = EXCLUDED.eclipse_fraction,
                in_belt = EXCLUDED.in_belt,
                sep_active = EXCLUDED.sep_active,
                dsn_visible = EXCLUDED.dsn_visible,
                temp_sun_residual_k = EXCLUDED.temp_sun_residual_k,
                link_margin_residual_db = EXCLUDED.link_margin_residual_db,
                array_efficiency_ratio = EXCLUDED.array_efficiency_ratio,
                voltage_residual_v = EXCLUDED.voltage_residual_v,
                dose_rate_ratio = EXCLUDED.dose_rate_ratio,
                temp_elec_rate_k_min = EXCLUDED.temp_elec_rate_k_min,
                soc_rate_pct_hr = EXCLUDED.soc_rate_pct_hr,
                dose_rate_delta_mrad_hr = EXCLUDED.dose_rate_delta_mrad_hr,
                signal_quality_delta = EXCLUDED.signal_quality_delta
        """), msg.model_dump())

    def _process_message(self, topic: str, key: str, value: bytes):
        """Route message to appropriate handler based on topic and payload."""
        try:
            payload = json.loads(value.decode())
        except json.JSONDecodeError as e:
            print(f"Failed to decode message: {e}")
            return

        session = SessionLocal()
        try:
            if topic == "trajectory":
                msg = SyntheticStateSnapshot(**payload)
                self._insert_state(session, msg)
            elif topic == "telemetry":
                table = self._get_telemetry_table(payload)
                if table == "thermal_output":
                    msg = SyntheticThermalOutput(**payload)
                    self._insert_thermal(session, msg)
                elif table == "power_output":
                    msg = SyntheticPowerOutput(**payload)
                    self._insert_power(session, msg)
                elif table == "comms_output":
                    msg = SyntheticCommsOutput(**payload)
                    self._insert_comms(session, msg)
                elif table == "radiation_output":
                    msg = SyntheticRadiationOutput(**payload)
                    self._insert_radiation(session, msg)
                elif table == "telemetry_packet":
                    msg = SyntheticTelemetryPacket(**payload)
                    self._insert_packet(session, msg)
                else:
                    print(f"Unknown telemetry type: {list(payload.keys())[:5]}")
                    return
            elif topic == "cross_model_state":
                msg = SyntheticCrossModelState(**payload)
                self._insert_cross_model(session, msg)
            elif topic == "events":
                msg = SyntheticAnomalyEvent(**payload)
                self._insert_anomaly(session, msg)
            elif topic == "ml_features":
                msg = SyntheticMLFeatureVector(**payload)
                self._insert_ml_features(session, msg)
            else:
                print(f"Unknown topic: {topic}")
                return

            session.commit()
            print(f"Inserted {topic} message for {payload.get('timestamp_utc', 'unknown')}")

        except Exception as e:  # noqa: BLE001 - keep consuming after any bad message
            session.rollback()
            print(f"Error processing {topic} message: {e}")
        finally:
            session.close()

    def run(self):
        """Main consumer loop."""
        self.running = True
        self.consumer.subscribe(TOPICS)
        print(f"Subscribed to topics: {TOPICS}")

        while self.running:
            msg = self.consumer.poll(1.0)
            if msg is None:
                continue
            if msg.error():
                if msg.error().code() == KafkaError._PARTITION_EOF:
                    continue
                print(f"Consumer error: {msg.error()}")
                continue

            self._process_message(msg.topic(), msg.key().decode() if msg.key() else "", msg.value())

        self.consumer.close()
        print("Consumer stopped")


def main():
    consumer = TelemetryConsumer()
    consumer.run()


if __name__ == "__main__":
    main()