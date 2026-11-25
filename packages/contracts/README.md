# contracts

The shared data definitions every other package imports: the ODCS data contracts, the
Pydantic models that follow them, and the planned mission timeline. It depends only on
`pydantic`.

| Path | Holds | Used by |
|------|-------|---------|
| `src/odcs/*.odcs.yaml` | Five ODCS v3.1.0 contracts (`01_state_engine` ... `05_anomaly_ml_features`): every synthetic field's type, unit and quality rules. The source of truth | People; the models below follow them |
| `src/contracts/models.py` | Pydantic models: the synthetic messages (`Synthetic*`), the real-data records (`OrionEphemeris`, `DonkiEvent`, ...), and the API response wrappers (`*Response`) | `physics_models` (messages), `backend` (responses), dashboard (client) |
| `src/contracts/planned_attitude.py` | The mission timeline: 108 attitude segments by mission elapsed time, extracted from NASA's Artemis II Overview Timeline. **Draft**: not checked against the PDF row by row | `physics_models` (solar angles), `pipelines.ingest.mission_events` |

Field names are lowercase snake_case everywhere, so a field keeps its name from the
simulator through Kafka, the database and the API to the dashboard.

How well the simulator meets the contracts:
[`docs/integration/CONTRACT_COMPLIANCE.md`](../../docs/integration/CONTRACT_COMPLIANCE.md).

## Changing a contract

Edit the YAML, then the matching model in `models.py`. If the field is stored, the
backend ORM model and a new Alembic migration follow (`packages/backend/README.md`), and
`physics_models/packet/validation.py` if a rule spans fields.

## Tests

```bash
uv run pytest tests/unit/contracts
```
