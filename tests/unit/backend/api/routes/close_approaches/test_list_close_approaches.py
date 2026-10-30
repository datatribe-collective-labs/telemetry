def test_list_close_approaches_defaults_dist_max(client, fake_session, row_factory, result_factory):
    from contracts import CloseApproach
    fake_session.results=[result_factory(scalar_value=1), result_factory([row_factory(CloseApproach.model_fields.keys())])]
    r=client.get('/close-approaches?designation=2026')
    assert r.status_code==200
    assert fake_session.calls[0][1]['dist_max_au']==0.05
    assert fake_session.calls[0][1]['designation']=='%2026%'
    assert 'des ILIKE :designation' in fake_session.calls[0][0]
