from backend.api.routes.synthetic import TELEMETRY_COLUMNS


def test_get_synthetic_telemetry_packet_returns_item(client, fake_session, row_factory, result_factory):
    fake_session.results=[result_factory([row_factory(TELEMETRY_COLUMNS)])]
    r=client.get('/telemetry/synthetic/packet/2026-04-01T12:00:00Z')
    assert r.status_code == 200
    assert r.json()['timestamp_utc'].startswith('2026-04-01T12:00:00')
    assert 'FROM telemetry_packet' in fake_session.calls[0][0]

def test_get_synthetic_telemetry_packet_404(client, fake_session, result_factory):
    fake_session.results=[result_factory([])]
    r=client.get('/telemetry/synthetic/packet/2026-04-01T12:00:00Z')
    assert r.status_code == 404
    assert r.json()['detail'] == 'Telemetry packet not found'
