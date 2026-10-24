def test_health_check(client):
    r=client.get('/health')
    assert r.status_code==200
    assert r.json()=={'status':'ok','service':'telemetry-api','version':'0.1.0'}
