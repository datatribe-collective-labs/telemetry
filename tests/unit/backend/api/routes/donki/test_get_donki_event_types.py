def test_get_donki_event_types(client):
    r=client.get('/donki/event-types')
    assert r.status_code==200
    assert 'CME' in r.json() and 'SEP' in r.json()
