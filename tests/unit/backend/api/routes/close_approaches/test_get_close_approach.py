def test_get_close_approach_404(client, fake_session, result_factory):
    fake_session.results=[result_factory([])]
    r=client.get('/close-approaches/A/B/2026-04-01T12:00:00Z')
    assert r.status_code==404
    assert r.json()['detail']=='Close approach not found'
