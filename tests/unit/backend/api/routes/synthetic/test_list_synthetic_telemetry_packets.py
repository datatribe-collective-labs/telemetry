from backend.api.routes.synthetic import TELEMETRY_COLUMNS


def test_list_synthetic_telemetry_packets(client, fake_session, row_factory, result_factory):
    fake_session.results=[result_factory(scalar_value=1), result_factory([row_factory(TELEMETRY_COLUMNS)])]
    r=client.get('/telemetry/synthetic/packet?all_nominal=false')
    assert r.status_code == 200
    body=r.json()
    assert body['total'] == 1
    assert body['limit'] == 100 and body['offset'] == 0
    assert body['items'][0]['timestamp_utc'].startswith('2026-04-01T12:00:00')
    assert 'FROM telemetry_packet' in fake_session.calls[1][0]
    assert fake_session.calls[0][1]['all_nominal'] == False
