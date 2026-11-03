from backend.api.routes.synthetic import TELEMETRY_COLUMNS


def test_get_latest_synthetic_telemetry_returns_item(client, fake_session, row_factory, result_factory):
    fake_session.results=[result_factory([row_factory(TELEMETRY_COLUMNS)])]
    r=client.get('/telemetry/synthetic/latest')
    assert r.status_code == 200
    assert r.json()['spacecraft_id'] == 'ORION_EM2'
    assert 'ORDER BY ingested_at DESC, timestamp_utc DESC' in fake_session.calls[0][0]

def test_get_latest_synthetic_telemetry_empty_is_null(client, fake_session, result_factory):
    fake_session.results=[result_factory([])]
    r=client.get('/telemetry/synthetic/latest')
    assert r.status_code == 200
    assert r.json() is None


def test_get_latest_synthetic_telemetry_orders_by_write_time(client, fake_session, result_factory):
    # After a restart at an earlier MET, an older run's later timestamps must not win.
    fake_session.results=[result_factory([])]
    client.get('/telemetry/synthetic/latest')
    assert 'ORDER BY ingested_at DESC' in fake_session.calls[0][0]
