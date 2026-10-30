def test_list_goes_integral_protons(client, fake_session, row_factory, result_factory):
    from contracts import GoesIntegralProtons
    fake_session.results = [
        result_factory(scalar_value=1),
        result_factory([row_factory(GoesIntegralProtons.model_fields.keys())])
    ]
    r = client.get('/iswa-goes-protons?date_from=2026-04-01T00:00:00Z')
    assert r.status_code == 200
    assert r.json()['total'] == 1
    assert fake_session.calls[0][1]['date_from'] is not None