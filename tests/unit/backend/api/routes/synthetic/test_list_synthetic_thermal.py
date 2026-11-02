from backend.api.routes.synthetic import THERMAL_COLUMNS


def test_list_synthetic_thermal(client, fake_session, row_factory, result_factory):
    fake_session.results=[result_factory(scalar_value=1), result_factory([row_factory(THERMAL_COLUMNS)])]
    r=client.get('/telemetry/synthetic/thermal?thermal_state=INFO')
    assert r.status_code == 200
    body=r.json()
    assert body['total'] == 1
    assert body['limit'] == 100 and body['offset'] == 0
    assert body['items'][0]['timestamp_utc'].startswith('2026-04-01T12:00:00')
    assert 'FROM thermal_output' in fake_session.calls[1][0]
    assert 'thermal_state = :thermal_state' in fake_session.calls[0][0]
    assert fake_session.calls[0][1]['thermal_state'] == 'INFO'


def test_list_synthetic_thermal_orders_newest_first_when_desc(client, fake_session, result_factory):
    fake_session.results=[result_factory(scalar_value=0), result_factory([])]
    r=client.get('/telemetry/synthetic/thermal?order=desc')
    assert r.status_code == 200
    assert 'ORDER BY timestamp_utc DESC' in fake_session.calls[1][0]


def test_list_synthetic_thermal_rejects_invalid_order(client):
    r=client.get('/telemetry/synthetic/thermal?order=newest')
    assert r.status_code == 422
