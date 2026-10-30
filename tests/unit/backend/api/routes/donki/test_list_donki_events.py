def test_list_donki_events(client, fake_session, row_factory, result_factory):
    from contracts import DonkiEvent
    fake_session.results=[result_factory(scalar_value=1), result_factory([row_factory(DonkiEvent.model_fields.keys())])]
    r=client.get('/donki?event_types=CME,SEP')
    assert r.status_code==200
    assert r.json()['total']==1
    assert fake_session.calls[0][1]['event_types']==['CME','SEP']

def test_list_donki_events_invalid_type(client):
    r=client.get('/donki?event_types=CME,BOGUS')
    assert r.status_code==400
