def test_get_orion_ephemeris_404(client, fake_session, result_factory):
    fake_session.results=[result_factory([])]
    r=client.get('/orion/-1024/2026-04-01T12:00:00Z')
    assert r.status_code==404
