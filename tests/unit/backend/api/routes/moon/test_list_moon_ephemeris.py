def test_list_moon_ephemeris_filters_by_time(client, fake_session, row_factory, result_factory):
    from contracts import MoonEphemeris
    fake_session.results = [result_factory(scalar_value=1), result_factory([row_factory(MoonEphemeris.model_fields.keys())])]

    r = client.get("/moon?date_from=2026-04-01T22:00:00Z&date_to=2026-04-02T00:00:00Z")

    assert r.status_code == 200
    assert r.json()["total"] == 1
    assert r.json()["items"][0]["x_km"] == 1.234
    assert "epoch >= :date_from AND epoch <= :date_to" in fake_session.calls[0][0]


def test_list_moon_ephemeris_without_filters_has_no_where_clause(client, fake_session, result_factory):
    fake_session.results = [result_factory(scalar_value=0), result_factory([])]

    r = client.get("/moon")

    assert r.status_code == 200
    assert r.json()["items"] == []
    assert "WHERE" not in fake_session.calls[0][0]
