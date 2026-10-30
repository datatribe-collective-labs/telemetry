def test_list_dsn_site_geometry(client, fake_session, row_factory, result_factory):
    from contracts import DsnSiteGeometry
    fake_session.results = [
        result_factory(scalar_value=1),
        result_factory([row_factory(DsnSiteGeometry.model_fields.keys())])
    ]
    r = client.get('/dsn-geometry?site=DSS-14&visible_only=true')
    assert r.status_code == 200
    assert r.json()['total'] == 1
    assert fake_session.calls[0][1]['site'] == 'DSS-14'
    assert 'visible = true' in fake_session.calls[0][0]