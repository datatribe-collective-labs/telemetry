def test_list_orion_ephemeris(client, fake_session, row_factory, result_factory):
    from contracts import OrionEphemeris
    fake_session.results=[result_factory(scalar_value=1), result_factory([row_factory(OrionEphemeris.model_fields.keys())])]
    r=client.get('/orion?date_to=2026-04-02T00:00:00Z')
    assert r.status_code==200
    assert r.json()['total']==1
    assert 'epoch <= :date_to' in fake_session.calls[0][0]
