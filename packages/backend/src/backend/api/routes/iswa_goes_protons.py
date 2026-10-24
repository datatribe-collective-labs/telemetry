"""API routes for NASA CCMC iSWA GOES integral proton flux."""

from datetime import datetime
from typing import Annotated

from contracts import GoesIntegralProtons, GoesIntegralProtonsResponse
from fastapi import APIRouter, Depends, Query
from sqlalchemy import text
from sqlalchemy.orm import Session

from backend.db import get_db

router = APIRouter(prefix="/iswa-goes-protons", tags=["iswa-goes-protons"])


@router.get("", response_model=GoesIntegralProtonsResponse)
async def list_goes_integral_protons(
    db: Annotated[Session, Depends(get_db)],
    date_from: datetime | None = Query(None, description="Start date (UTC)"),
    date_to: datetime | None = Query(None, description="End date (UTC)"),
    limit: int = Query(100, ge=1, le=1000, description="Maximum results"),
    offset: int = Query(0, ge=0, description="Pagination offset"),
) -> GoesIntegralProtonsResponse:
    """List GOES integral proton flux records with optional filters."""
    conditions = []
    params: dict[str, object] = {}

    if date_from:
        conditions.append("time >= :date_from")
        params["date_from"] = date_from
    if date_to:
        conditions.append("time < :date_to")
        params["date_to"] = date_to

    where_clause = "WHERE " + " AND ".join(conditions) if conditions else ""

    # Count total
    count_query = f"SELECT COUNT(*) FROM goes_integral_protons {where_clause}"
    total = db.execute(text(count_query), params).scalar() or 0

    # Fetch items
    select_query = f"""
        SELECT time, proton_satellite,
               p1_pfu, p5_pfu, p10_pfu, p30_pfu,
               p50_pfu, p60_pfu, p100_pfu, p500_pfu,
               ingested_at
        FROM goes_integral_protons
        {where_clause}
        ORDER BY time
        LIMIT :limit OFFSET :offset
    """
    params["limit"] = limit
    params["offset"] = offset

    result = db.execute(text(select_query), params)
    items = [GoesIntegralProtons.model_validate(dict(row._mapping)) for row in result]

    return GoesIntegralProtonsResponse(
        items=items,
        total=total,
        limit=limit,
        offset=offset,
    )


@router.get("/{time}", response_model=GoesIntegralProtons)
async def get_goes_integral_protons(
    time: datetime,
    db: Annotated[Session, Depends(get_db)],
) -> GoesIntegralProtons:
    """Get a specific GOES integral proton flux record by primary key."""
    query = """
        SELECT time, proton_satellite,
               p1_pfu, p5_pfu, p10_pfu, p30_pfu,
               p50_pfu, p60_pfu, p100_pfu, p500_pfu,
               ingested_at
        FROM goes_integral_protons
        WHERE time = :time
    """
    result = db.execute(text(query), {"time": time})
    row = result.first()
    if not row:
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail="GOES integral proton record not found")

    return GoesIntegralProtons.model_validate(dict(row._mapping))