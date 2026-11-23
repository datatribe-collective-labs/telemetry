from datetime import UTC, datetime

import httpx

from dashboard.src.prototype.data.backend_api import BackendAPI

WHEN = datetime(2026, 4, 6, tzinfo=UTC)
COMMS_ROW = {
    "timestamp_utc": WHEN.isoformat(), "eirp_dbw": 20.0, "free_space_path_loss_db": 220.0,
    "received_power_dbw": -150.0, "eb_n0_db": 10.0, "link_margin_db": 3.0, "data_rate_kbps": 256.0,
    "signal_quality": 0.9, "comm_state": "NO_LINK", "link_loss_reason": "MOON_BLOCKED",
}
RADIATION_ROW = {
    "timestamp_utc": WHEN.isoformat(), "total_dose_rate_rad_s": 1e-6, "cumulative_dose_krad": 0.001,
    "solar_array_degradation": 1.0, "thermal_alpha_degradation": 1.0, "thermal_eps_degradation": 1.0,
    "radiation_dose_rate_mrad_hr": 3.6, "sep_event_active": False, "radiation_zone": "DEEP_SPACE",
}


def api_returning(row):
    requests = []

    def handler(request):
        requests.append(request)
        return httpx.Response(200, json={"items": [row], "total": 1, "limit": 100, "offset": 0})

    api = BackendAPI("http://test")
    api._client = httpx.Client(base_url="http://test", transport=httpx.MockTransport(handler))
    return api, requests


def test_get_synthetic_comms_returns_the_link_loss_reason():
    api, requests = api_returning(COMMS_ROW)
    resp = api.get_synthetic_comms(date_from=WHEN, limit=10, order="asc", sort_by="timestamp_utc")
    assert resp.items[0].link_loss_reason == "MOON_BLOCKED"
    assert requests[0].url.path == "/telemetry/synthetic/comms"
    assert requests[0].url.params["limit"] == "10"
    assert requests[0].url.params["sort_by"] == "timestamp_utc"


def test_get_synthetic_radiation_returns_the_zone():
    api, requests = api_returning(RADIATION_ROW)
    resp = api.get_synthetic_radiation(sep_event_active=False)
    assert resp.items[0].radiation_zone == "DEEP_SPACE"
    assert requests[0].url.path == "/telemetry/synthetic/radiation"
    assert requests[0].url.params["sep_event_active"] == "false"
