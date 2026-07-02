"""
api/routers/vehicles.py
------------------------
GET /vehicles    → list vehicles with filters
"""

from __future__ import annotations

from typing import Annotated
from fastapi import APIRouter, Query

from scraper.utils.supabase_client import get_client
from config.settings import get_settings

router = APIRouter()
settings = get_settings()


@router.get("")
def list_vehicles(
    color: Annotated[str | None, Query(description="Primary vehicle color")] = None,
    type_slug: Annotated[str | None, Query(description="Vehicle type slug")] = None,
    min_capacity: Annotated[int | None, Query(ge=1)] = None,
    max_capacity: Annotated[int | None, Query(ge=1)] = None,
    state: Annotated[str | None, Query(description="Filter by company state")] = None,
    page: Annotated[int, Query(ge=1)] = 1,
    limit: Annotated[int, Query(ge=1, le=100)] = settings.API_DEFAULT_PAGE_SIZE,
):
    """
    List vehicles with optional color, type, capacity, and state filters.
    """
    db = get_client()

    query = (
        db.table("vehicles")
        .select(
            "id, name, description, capacity, primary_color, secondary_color, "
            "amenities, price_per_hour, price_per_day, "
            "vehicle_types(slug, label), "
            "companies(id, name, city, state, phone, url, rating)"
        )
    )

    if color:
        query = query.eq("primary_color", color)

    if min_capacity:
        query = query.gte("capacity", min_capacity)
    if max_capacity:
        query = query.lte("capacity", max_capacity)

    # State filter joins through the companies relation
    # Supabase supports filtering on nested/foreign-key columns
    if state:
        query = query.eq("companies.state", state.upper())

    # vehicle type filter via join
    if type_slug:
        query = query.eq("vehicle_types.slug", type_slug)

    offset = (page - 1) * limit
    result = query.range(offset, offset + limit - 1).execute()

    return {
        "page": page,
        "limit": limit,
        "count": len(result.data),
        "data": result.data,
    }