
def test_state_date_filters_and_pagination(client, fake_session, row_factory, result_factory):
    fake_session.results=[result_factory(scalar_value=0), result_factory([])]
    r=client.get('/telemetry/synthetic/state?date_from=2026-04-01T00:00:00Z&date_to=2026-04-02T00:00:00Z&limit=10&offset=3')
    assert r.status_code==200
    sql, params=fake_session.calls[0]
    assert 'timestamp_utc >= :date_from' in sql and 'timestamp_utc < :date_to' in sql
    assert params.get('limit', True)
    assert fake_session.calls[1][1]['limit']==10 and fake_session.calls[1][1]['offset']==3

def test_state_pagination_validation(client, fake_session):
    for query in ('limit=0','limit=1001','offset=-1'):
        assert client.get('/telemetry/synthetic/state?'+query).status_code==422
