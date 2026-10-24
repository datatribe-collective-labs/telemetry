import re

import contracts
from backend.api.routes import synthetic
from backend.models import Base

PAIRS=[
 ('state_snapshot','STATE_COLUMNS','SyntheticStateSnapshot'),
 ('thermal_output','THERMAL_COLUMNS','SyntheticThermalOutput'),
 ('power_output','POWER_COLUMNS','SyntheticPowerOutput'),
 ('comms_output','COMMS_COLUMNS','SyntheticCommsOutput'),
 ('radiation_output','RADIATION_COLUMNS','SyntheticRadiationOutput'),
 ('cross_model_state','CROSS_MODEL_COLUMNS','SyntheticCrossModelState'),
 ('telemetry_packet','TELEMETRY_COLUMNS','SyntheticTelemetryPacket'),
 ('anomaly_events','ANOMALY_COLUMNS','SyntheticAnomalyEvent'),
 ('ml_feature_vectors','ML_FEATURE_COLUMNS','SyntheticMLFeatureVector'),
]

def test_column_lists_match_db_and_contracts():
    for table_name, constant_name, model_name in PAIRS:
        cols=getattr(synthetic, constant_name)
        db_names=[]
        for c in cols:
            if ' AS ' in c:
                db_names.append(c.split('::',1)[0])
            else:
                db_names.append(c.lower())
        assert db_names == [c.name for c in Base.metadata.tables[table_name].columns]
        output_names=[]
        for c in cols:
            if ' AS ' in c:
                output_names.append(re.search(r'AS\s+"([^"]+)"', c).group(1))
            else:
                output_names.append(c)
        assert output_names == list(getattr(contracts, model_name).model_fields)
