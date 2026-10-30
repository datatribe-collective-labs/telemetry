def test_get_donki_event_404(client, fake_session, result_factory):
    fake_session.results=[result_factory([])]
    r=client.get('/donki/CME/nope')
    assert r.status_code==404
    assert r.json()['detail']=='DONKI event not found'

def test_get_donki_event_invalid_type(client):
    r=client.get('/donki/BOGUS/nope')
    assert r.status_code==400
