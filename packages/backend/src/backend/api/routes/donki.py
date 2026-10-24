"""API routes for NASA DONKI space weather events."""

from datetime import datetime
from typing import Annotated

from contracts import DonkiEvent, DonkiEventResponse
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import text
from sqlalchemy.orm import Session

from backend.db import get_db

router = APIRouter(prefix="/donki", tags=["donki"])


DONKI_EVENT_TYPES = (
    "CME",
    "CMEAnalysis",
    "SEP",
    "FLR",
    "IPS",
    "GST",
    "RBE",
    "HSS",
    "MPC",
    "WSAEnlilSimulations",
)


@router.get("", response_model=DonkiEventResponse)
async def list_donki_events(
    db: Annotated[Session, Depends(get_db)],
    date_from: datetime | None = Query(None, description="Start date (UTC)"),
    date_to: datetime | None = Query(None, description="End date (UTC)"),
    event_types: str | None = Query(None, description="Comma-separated event types (e.g., CME,SEP,FLR)"),
    limit: int = Query(100, ge=1, le=1000, description="Maximum results"),
    offset: int = Query(0, ge=0, description="Pagination offset"),
) -> DonkiEventResponse:
    """List DONKI space weather events with optional filters."""
    conditions = []
    params: dict[str, object] = {}

    if date_from:
        conditions.append("COALESCE(event_time, start_time) >= :date_from")
        params["date_from"] = date_from
    if date_to:
        conditions.append("COALESCE(event_time, start_time) < :date_to")
        params["date_to"] = date_to

    parsed_event_types = None
    if event_types:
        parsed_event_types = [t.strip() for t in event_types.split(",")]
        # Validate event types
        for et in parsed_event_types:
            if et not in DONKI_EVENT_TYPES:
                raise HTTPException(
                    status_code=400,
                    detail=f"Invalid event type: {et}. Valid types: {', '.join(DONKI_EVENT_TYPES)}",
                )
        conditions.append("event_type = ANY(:event_types)")
        params["event_types"] = parsed_event_types

    where_clause = "WHERE " + " AND ".join(conditions) if conditions else ""

    # Count total
    count_query = f"SELECT COUNT(*) FROM donki_events {where_clause}"
    total = db.execute(text(count_query), params).scalar() or 0

    # Fetch items
    select_query = f"""
        SELECT event_type, event_id, start_time, end_time, event_time,
               fetched_at, source_url, payload
        FROM donki_events
        {where_clause}
        ORDER BY COALESCE(event_time, start_time), event_type, event_id
        LIMIT :limit OFFSET :offset
    """
    params["limit"] = limit
    params["offset"] = offset

    result = db.execute(text(select_query), params)
    items = [DonkiEvent.model_validate(dict(row._mapping)) for row in result]

    return DonkiEventResponse(
        items=items,
        total=total,
        limit=limit,
        offset=offset,
    )


@router.get("/event-types", response_model=list[str])
async def get_donki_event_types() -> list[str]:
    """Get list of supported DONKI event types."""
    return list(DONKI_EVENT_TYPES)


@router.get("/{event_type}/{event_id}", response_model=DonkiEvent)
async def get_donki_event(
    event_type: str,
    event_id: str,
    db: Annotated[Session, Depends(get_db)],
) -> DonkiEvent:
    """Get a specific DONKI event by primary key."""
    if event_type not in DONKI_EVENT_TYPES:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid event type: {event_type}. Valid types: {', '.join(DONKI_EVENT_TYPES)}",
        )

    query = """
        SELECT event_type, event_id, start_time, end_time, event_time,
               fetched_at, source_url, payload
        FROM donki_events
        WHERE event_type = :event_type AND event_id = :event_id
    """
    result = db.execute(text(query), {"event_type": event_type, "event_id": event_id})
    row = result.first()
    if not row:
        raise HTTPException(status_code=404, detail="DONKI event not found")

    return DonkiEvent.model_validate(dict(row._mapping))