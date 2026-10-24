from backend.api.routes.synthetic import STATE_COLUMNS


def test_get_synthetic_state_returns_item(client, fake_session, row_factory, result_factory):
    fake_session.results=[result_factory([row_factory(STATE_COLUMNS)])]
    r=client.get('/telemetry/synthetic/state/2026-04-01T12:00:00Z')
    assert r.status_code == 200
    assert r.json()['timestamp_utc'].startswith('2026-04-01T12:00:00')
    assert 'FROM state_snapshot' in fake_session.calls[0][0]

def test_get_synthetic_state_404(client, fake_session, result_factory):
    fake_session.results=[result_factory([])]
    r=client.get('/telemetry/synthetic/state/2026-04-01T12:00:00Z')
    assert r.status_code == 404
    assert r.json()['detail'] == 'State snapshot not found'
