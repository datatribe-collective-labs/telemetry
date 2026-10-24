from backend.api.routes.synthetic import TELEMETRY_COLUMNS


def test_get_latest_synthetic_telemetry_returns_item(client, fake_session, row_factory, result_factory):
    fake_session.results=[result_factory([row_factory(TELEMETRY_COLUMNS)])]
    r=client.get('/telemetry/synthetic/latest')
    assert r.status_code == 200
    assert r.json()['spacecraft_id'] == 'ORION_EM2'
    assert 'ORDER BY timestamp_utc DESC' in fake_session.calls[0][0]

def test_get_latest_synthetic_telemetry_empty_is_null(client, fake_session, result_factory):
    fake_session.results=[result_factory([])]
    r=client.get('/telemetry/synthetic/latest')
    assert r.status_code == 200
    assert r.json() is None
