
def test_get_dsn_site_geometry_404(client, fake_session):
    fake_session.results = []
    r = client.get('/dsn-geometry/-1024/DSS-14/2026-04-01T12:00:00Z')
    assert r.status_code == 404