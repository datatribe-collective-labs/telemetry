"""Shared fixtures for DONKI ingestion tests."""

from datetime import datetime, timezone
from unittest.mock import MagicMock

import pytest


@pytest.fixture
def mock_connection():
    cursor = MagicMock()
    conn = MagicMock()
    conn.cursor.return_value.__enter__.return_value = cursor
    conn.mock_cursor = cursor
    return conn


@pytest.fixture
def cme_payload():
    return [
        {
            "activityID": "2026-04-01T23:45:00-CME-001",
            "startTime": "2026-04-01T23:45Z",
            "sourceLocation": "N28W25",
            "activeRegionNum": 14179,
            "note": "test record",
        },
        {
            "activityID": "2026-04-02T04:00:00-CME-002",
            "startTime": "2026-04-02T04:00:00Z",
            "endTime": "2026-04-02T05:00:00Z",
        },
    ]


@pytest.fixture
def sep_payload():
    return [
        {
            "sepID": "2026-04-01T12:00:00-SEP-001",
            "eventTime": "2026-04-01T12:00Z",
            "peakTime": "2026-04-01T14:30Z",
            "energy": ">10 MeV",
        }
    ]


@pytest.fixture
def flr_payload():
    return [
        {
            "flrID": "2026-04-01T08:00:00-FLR-001",
            "beginTime": "2026-04-01T08:00Z",
            "peakTime": "2026-04-01T08:15Z",
            "classType": "M1.2",
        }
    ]


@pytest.fixture
def gst_payload():
    return [
        {
            "gstID": "2026-04-01T00:00:00-GST-001",
            "startTime": "2026-04-01T00:00Z",
            "kpIndex": 7,
        }
    ]


@pytest.fixture
def donki_event_cme(cme_payload):
    from pipelines.ingest.donki import DonkiEvent

    return DonkiEvent.from_api_record(
        "CME",
        cme_payload[0],
        "https://ccmc.gsfc.nasa.gov/DONKI-API/get/CME?startDate=2026-04-01&endDate=2026-04-10",
    )