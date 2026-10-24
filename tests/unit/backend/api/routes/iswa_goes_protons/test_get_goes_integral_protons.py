
def test_get_goes_integral_protons_404(client, fake_session):
    fake_session.results = []
    r = client.get('/iswa-goes-protons/2026-04-01T12:00:00Z')
    assert r.status_code == 404