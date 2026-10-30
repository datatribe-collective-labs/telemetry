"""API routes for the Artemis II mission timeline (planned attitude segments).

DRAFT data: extracted from the graphical overview-timeline PDF, not yet
fact-checked against it (see pipelines/ingest/mission_events.py).
"""

from typing import Annotated

from contracts import MissionEvent, MissionEventResponse
from fastapi import APIRouter, Depends, Query
from sqlalchemy import text
from sqlalchemy.orm import Session

from backend.db import get_db

router = APIRouter(prefix="/mission-events", tags=["mission-events"])


@router.get("", response_model=MissionEventResponse)
async def list_mission_events(
    db: Annotated[Session, Depends(get_db)],
    met_from_s: float | None = Query(None, description="MET start filter (seconds)"),
    met_to_s: float | None = Query(None, description="MET end filter (seconds, exclusive)"),
    mode: str | None = Query(None, description="Filter by attitude mode (e.g. BURN_TLI)"),
) -> MissionEventResponse:
    """List planned mission segments in MET order (overlapping window filter)."""
    conditions = []
    params: dict[str, object] = {}
    if met_from_s is not None:
        conditions.append("met_end_s > :met_from_s")
        params["met_from_s"] = met_from_s
    if met_to_s is not None:
        conditions.append("met_start_s < :met_to_s")
        params["met_to_s"] = met_to_s
    if mode:
        conditions.append("mode = :mode")
        params["mode"] = mode
    where_clause = "WHERE " + " AND ".join(conditions) if conditions else ""

    total = db.execute(text(f"SELECT COUNT(*) FROM mission_events {where_clause}"), params).scalar() or 0
    rows = db.execute(
        text(f"""
            SELECT met_start_s, met_end_s, mode, description
            FROM mission_events
            {where_clause}
            ORDER BY met_start_s
        """),
        params,
    ).mappings().all()

    return MissionEventResponse(
        items=[MissionEvent.model_validate(dict(r)) for r in rows],
        total=total,
    )
