def test_health_check_db_ok(client, fake_session, result_factory):
    fake_session.results=[result_factory(scalar_value=1)]
    r=client.get('/health/db')
    assert r.status_code==200 and r.json()['status']=='ok'

def test_health_check_db_degraded(client, fake_session):
    def execute(*a,**k): raise RuntimeError('down')
    fake_session.execute=execute
    r=client.get('/health/db')
    assert r.status_code==200 and r.json()['status']=='degraded'
