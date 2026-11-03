"""Backend API client for Streamlit prototype.

Connects to FastAPI backend at http://localhost:8000 by default.
All endpoints return Pydantic models from contracts package.

The client is synchronous: Streamlit runs each session's script on its own
thread, and one shared httpx.Client is safe to use across those threads
(an AsyncClient is bound to the event loop that created it).
"""

from datetime import datetime
from typing import Any

import httpx
import streamlit as st
from contracts import (
    CloseApproachResponse,
    DonkiEventResponse,
    DsnSiteGeometryResponse,
    GoesIntegralProtonsResponse,
    HealthResponse,
    OrionEphemerisResponse,
    SyntheticPowerResponse,
    SyntheticStateResponse,
    SyntheticTelemetryPacket,
    SyntheticTelemetryPacketResponse,
    SyntheticThermalResponse,
)

# The backend rejects `limit` above this on every list endpoint (Query le=1000).
MAX_LIMIT = 1000


class BackendAPIError(Exception):
    """Backend unreachable or returned an error; message is safe to show in the UI."""


class BackendAPI:
    """Sync HTTP client for FastAPI backend."""

    def __init__(self, base_url: str = "http://localhost:8000", timeout: float = 10.0):
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout
        self._client = httpx.Client(base_url=self.base_url, timeout=self.timeout)

    def close(self):
        self._client.close()

    def _get(self, path: str, params: dict | None = None, response_model: Any = None) -> Any:
        try:
            resp = self._client.get(path, params=params)
            resp.raise_for_status()
        except httpx.HTTPStatusError as e:
            raise BackendAPIError(
                f"Backend returned {e.response.status_code} for {path}: {e.response.text[:200]}"
            ) from e
        except httpx.HTTPError as e:
            raise BackendAPIError(f"Cannot reach backend at {self.base_url} ({e})") from e
        data = resp.json()
        if response_model:
            return response_model(**data)
        return data

    # =========================================================================
    # Synthetic Telemetry Endpoints
    # =========================================================================

    def get_synthetic_state(
        self,
        date_from: datetime | None = None,
        date_to: datetime | None = None,
        limit: int = 100,
        offset: int = 0,
        order: str = "desc",
        sort_by: str = "ingested_at",
    ) -> SyntheticStateResponse:
        params = {"limit": limit, "offset": offset, "order": order, "sort_by": sort_by}
        if date_from:
            params["date_from"] = date_from.isoformat()
        if date_to:
            params["date_to"] = date_to.isoformat()
        return self._get("/telemetry/synthetic/state", params, SyntheticStateResponse)

    def get_synthetic_thermal(
        self,
        date_from: datetime | None = None,
        date_to: datetime | None = None,
        thermal_state: str | None = None,
        limit: int = 100,
        offset: int = 0,
        order: str = "desc",
        sort_by: str = "ingested_at",
    ) -> SyntheticThermalResponse:
        params = {"limit": limit, "offset": offset, "order": order, "sort_by": sort_by}
        if date_from:
            params["date_from"] = date_from.isoformat()
        if date_to:
            params["date_to"] = date_to.isoformat()
        if thermal_state:
            params["thermal_state"] = thermal_state
        return self._get("/telemetry/synthetic/thermal", params, SyntheticThermalResponse)

    def get_synthetic_power(
        self,
        date_from: datetime | None = None,
        date_to: datetime | None = None,
        power_state: str | None = None,
        limit: int = 100,
        offset: int = 0,
        order: str = "desc",
        sort_by: str = "ingested_at",
    ) -> SyntheticPowerResponse:
        params = {"limit": limit, "offset": offset, "order": order, "sort_by": sort_by}
        if date_from:
            params["date_from"] = date_from.isoformat()
        if date_to:
            params["date_to"] = date_to.isoformat()
        if power_state:
            params["power_state"] = power_state
        return self._get("/telemetry/synthetic/power", params, SyntheticPowerResponse)

    def get_synthetic_packet(
        self,
        date_from: datetime | None = None,
        date_to: datetime | None = None,
        all_nominal: bool | None = None,
        thermal_state: str | None = None,
        power_state: str | None = None,
        comm_state: str | None = None,
        limit: int = 100,
        offset: int = 0,
        order: str = "desc",
        sort_by: str = "ingested_at",
    ) -> SyntheticTelemetryPacketResponse:
        params = {"limit": limit, "offset": offset, "order": order, "sort_by": sort_by}
        if date_from:
            params["date_from"] = date_from.isoformat()
        if date_to:
            params["date_to"] = date_to.isoformat()
        if all_nominal is not None:
            params["all_nominal"] = all_nominal
        if thermal_state:
            params["thermal_state"] = thermal_state
        if power_state:
            params["power_state"] = power_state
        if comm_state:
            params["comm_state"] = comm_state
        return self._get("/telemetry/synthetic/packet", params, SyntheticTelemetryPacketResponse)

    def get_latest_packet(self) -> SyntheticTelemetryPacket | None:
        data = self._get("/telemetry/synthetic/latest")
        if data:
            return SyntheticTelemetryPacket(**data)
        return None

    # =========================================================================
    # Real Data Endpoints
    # =========================================================================

    def get_orion_ephemeris(
        self,
        date_from: datetime | None = None,
        date_to: datetime | None = None,
        limit: int = 100,
        offset: int = 0,
    ) -> OrionEphemerisResponse:
        params = {"limit": limit, "offset": offset}
        if date_from:
            params["date_from"] = date_from.isoformat()
        if date_to:
            params["date_to"] = date_to.isoformat()
        return self._get("/orion", params, OrionEphemerisResponse)

    def get_goes_protons(
        self,
        date_from: datetime | None = None,
        date_to: datetime | None = None,
        limit: int = 100,
        offset: int = 0,
    ) -> GoesIntegralProtonsResponse:
        params = {"limit": limit, "offset": offset}
        if date_from:
            params["date_from"] = date_from.isoformat()
        if date_to:
            params["date_to"] = date_to.isoformat()
        return self._get("/iswa-goes-protons", params, GoesIntegralProtonsResponse)

    def get_dsn_geometry(
        self,
        date_from: datetime | None = None,
        date_to: datetime | None = None,
        site: str | None = None,
        complex: str | None = None,
        visible_only: bool = False,
        limit: int = 100,
        offset: int = 0,
    ) -> DsnSiteGeometryResponse:
        params = {"limit": limit, "offset": offset}
        if date_from:
            params["date_from"] = date_from.isoformat()
        if date_to:
            params["date_to"] = date_to.isoformat()
        if site:
            params["site"] = site
        if complex:
            params["complex"] = complex
        if visible_only:
            params["visible_only"] = "true"
        return self._get("/dsn-geometry", params, DsnSiteGeometryResponse)

    def get_close_approaches(
        self,
        date_from: datetime | None = None,
        date_to: datetime | None = None,
        dist_max_au: float = 0.05,
        designation: str | None = None,
        limit: int = 100,
        offset: int = 0,
    ) -> CloseApproachResponse:
        params = {"limit": limit, "offset": offset, "dist_max_au": dist_max_au}
        if date_from:
            params["date_from"] = date_from.isoformat()
        if date_to:
            params["date_to"] = date_to.isoformat()
        if designation:
            params["designation"] = designation
        return self._get("/close-approaches", params, CloseApproachResponse)

    def get_donki_events(
        self,
        date_from: datetime | None = None,
        date_to: datetime | None = None,
        event_types: list[str] | None = None,
        limit: int = 100,
        offset: int = 0,
    ) -> DonkiEventResponse:
        params = {"limit": limit, "offset": offset}
        if date_from:
            params["date_from"] = date_from.isoformat()
        if date_to:
            params["date_to"] = date_to.isoformat()
        if event_types:
            params["event_types"] = event_types
        return self._get("/donki", params, DonkiEventResponse)

    # =========================================================================
    # Health
    # =========================================================================

    def health_check(self) -> HealthResponse:
        return self._get("/health", response_model=HealthResponse)




# Pages import this name; the client itself is now synchronous.
SyncBackendAPI = BackendAPI


@st.cache_resource
def get_api(base_url: str = "http://localhost:8000") -> BackendAPI:
    """Get the process-wide API client (shared by all sessions)."""
    return BackendAPI(base_url)
