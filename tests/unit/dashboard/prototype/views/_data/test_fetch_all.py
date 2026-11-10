from types import SimpleNamespace

from dashboard.src.prototype.views._data import fetch_all


def paged_endpoint(total):
    """Fake list endpoint over rows 0..total-1, recording each call."""
    calls = []

    def fetch(limit, offset, **kwargs):
        calls.append({"limit": limit, "offset": offset, **kwargs})
        return SimpleNamespace(items=list(range(offset, min(offset + limit, total))), total=total)

    return fetch, calls


def test_fetch_all_pages_until_total_is_reached():
    fetch, calls = paged_endpoint(2500)
    items = fetch_all(fetch, page_size=1000)
    assert items == list(range(2500))
    assert [c["offset"] for c in calls] == [0, 1000, 2000]


def test_fetch_all_passes_filters_through_to_every_page():
    fetch, calls = paged_endpoint(1500)
    fetch_all(fetch, page_size=1000, date_from="a", order="desc")
    assert all(c["date_from"] == "a" and c["order"] == "desc" for c in calls)


def test_fetch_all_stops_at_max_rows():
    fetch, calls = paged_endpoint(10_000)
    items = fetch_all(fetch, page_size=1000, max_rows=2500)
    assert len(items) == 2500
    assert len(calls) == 3


def test_fetch_all_stops_on_an_empty_page():
    # e.g. `total` overstates what is left because rows were deleted mid-read
    def fetch(limit, offset):
        return SimpleNamespace(items=[] if offset else [1, 2], total=10)

    assert fetch_all(fetch, page_size=2) == [1, 2]


def test_fetch_all_handles_a_missing_response():
    assert fetch_all(lambda limit, offset: None) == []
