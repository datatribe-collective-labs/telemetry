from backend.api.routes.synthetic import ANOMALY_COLUMNS


def test_list_synthetic_anomalies(client, fake_session, row_factory, result_factory):
    fake_session.results=[result_factory(scalar_value=1), result_factory([row_factory(ANOMALY_COLUMNS)])]
    r=client.get('/telemetry/synthetic/anomalies?severity=INFO')
    assert r.status_code == 200
    body=r.json()
    assert body['total'] == 1
    assert body['limit'] == 100 and body['offset'] == 0
    assert body['items'][0]['timestamp_utc'].startswith('2026-04-01T12:00:00')
    assert 'FROM anomaly_events' in fake_session.calls[1][0]
    assert fake_session.calls[0][1]['severity'] == 'INFO'
