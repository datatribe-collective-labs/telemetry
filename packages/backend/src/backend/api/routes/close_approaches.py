"""API routes for JPL Close-Approach Data (CAD)."""

from datetime import datetime
from typing import Annotated

from contracts import CloseApproach, CloseApproachResponse
from fastapi import APIRouter, Depends, Query
from sqlalchemy import text
from sqlalchemy.orm import Session

from backend.db import get_db

router = APIRouter(prefix="/close-approaches", tags=["close-approaches"])


@router.get("", response_model=CloseApproachResponse)
async def list_close_approaches(
    db: Annotated[Session, Depends(get_db)],
    date_from: datetime | None = Query(None, description="Start date (UTC)"),
    date_to: datetime | None = Query(None, description="End date (UTC)"),
    dist_max_au: float = Query(0.05, description="Maximum distance in AU"),
    designation: str | None = Query(None, description="Filter by object designation (partial match)"),
    limit: int = Query(100, ge=1, le=1000, description="Maximum results"),
    offset: int = Query(0, ge=0, description="Pagination offset"),
) -> CloseApproachResponse:
    """List close approach events with optional filters."""
    conditions = []
    params: dict[str, object] = {}

    if date_from:
        conditions.append("close_approach_time >= :date_from")
        params["date_from"] = date_from
    if date_to:
        conditions.append("close_approach_time < :date_to")
        params["date_to"] = date_to
    if dist_max_au is not None:
        conditions.append("dist_au <= :dist_max_au")
        params["dist_max_au"] = dist_max_au
    if designation:
        conditions.append("des ILIKE :designation")
        params["designation"] = f"%{designation}%"

    where_clause = "WHERE " + " AND ".join(conditions) if conditions else ""

    # Count total
    count_query = f"SELECT COUNT(*) FROM close_approaches {where_clause}"
    total = db.execute(text(count_query), params).scalar() or 0

    # Fetch items
    select_query = f"""
        SELECT des, orbit_id, close_approach_jd, close_approach_time,
               dist_au, dist_min_au, dist_max_au,
               v_rel_kms, v_inf_kms, h_mag, body
        FROM close_approaches
        {where_clause}
        ORDER BY close_approach_time
        LIMIT :limit OFFSET :offset
    """
    params["limit"] = limit
    params["offset"] = offset

    result = db.execute(text(select_query), params)
    items = [CloseApproach.model_validate(dict(row._mapping)) for row in result]

    return CloseApproachResponse(
        items=items,
        total=total,
        limit=limit,
        offset=offset,
    )


@router.get("/{des}/{orbit_id}/{close_approach_time}", response_model=CloseApproach)
async def get_close_approach(
    des: str,
    orbit_id: str,
    close_approach_time: datetime,
    db: Annotated[Session, Depends(get_db)],
) -> CloseApproach:
    """Get a specific close approach by primary key."""
    query = """
        SELECT des, orbit_id, close_approach_jd, close_approach_time,
               dist_au, dist_min_au, dist_max_au,
               v_rel_kms, v_inf_kms, h_mag, body
        FROM close_approaches
        WHERE des = :des AND orbit_id = :orbit_id AND close_approach_time = :close_approach_time
    """
    result = db.execute(
        text(query),
        {"des": des, "orbit_id": orbit_id, "close_approach_time": close_approach_time},
    )
    row = result.first()
    if not row:
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail="Close approach not found")

    return CloseApproach.model_validate(dict(row._mapping))