from backend.api.routes.synthetic import STATE_COLUMNS


def test_list_synthetic_state(client, fake_session, row_factory, result_factory):
    fake_session.results=[result_factory(scalar_value=1), result_factory([row_factory(STATE_COLUMNS)])]
    r=client.get('/telemetry/synthetic/state')
    assert r.status_code == 200
    body=r.json()
    assert body['total']==1 and body['limit']==100 and body['offset']==0
    assert body['items'][0]['timestamp_utc'].startswith('2026-04-01T12:00:00')
    assert 'FROM state_snapshot' in fake_session.calls[1][0]
