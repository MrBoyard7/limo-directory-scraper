"""
api/routers/companies.py
-------------------------
GET /companies         → list (paginated, filterable)
GET /companies/{id}    → single company with vehicles + images
"""

from __future__ import annotations

from typing import Annotated
from fastapi import APIRouter, HTTPException, Query

from scraper.utils.supabase_client import get_client
from config.settings import get_settings

router = APIRouter()
settings = get_settings()


@router.get("")
def list_companies(
    state: Annotated[str | None, Query(description="Two-letter state code, e.g. TX")] = None,
    city: Annotated[str | None, Query(description="City name")] = None,
    vehicle_color: Annotated[str | None, Query(description="Primary vehicle color")] = None,
    vehicle_type: Annotated[str | None, Query(description="Vehicle type slug, e.g. party_bus")] = None,
    event_type: Annotated[str | None, Query(description="Event type slug, e.g. wedding")] = None,
    min_rating: Annotated[float | None, Query(description="Minimum Google rating (0–5)")] = None,
    page: Annotated[int, Query(ge=1)] = 1,
    limit: Annotated[int, Query(ge=1, le=100)] = settings.API_DEFAULT_PAGE_SIZE,
):
    """
    List companies with optional filters.
    Filtered via the `v_companies_enriched` view.
    """
    db = get_client()
    query = db.table("v_companies_enriched").select("*")

    if state:
        query = query.eq("state", state.upper())
    if city:
        query = query.ilike("city", f"%{city}%")
    if min_rating:
        query = query.gte("rating", min_rating)

    # Array-based filters (vehicle_colors, vehicle_type_slugs, event_type_slugs are arrays in the view)
    if vehicle_color:
        query = query.contains("vehicle_colors", [vehicle_color])
    if vehicle_type:
        query = query.contains("vehicle_type_slugs", [vehicle_type])
    if event_type:
        query = query.contains("event_type_slugs", [event_type])

    offset = (page - 1) * limit
    result = query.range(offset, offset + limit - 1).execute()

    return {
        "page": page,
        "limit": limit,
        "count": len(result.data),
        "data": result.data,
    }


@router.get("/{company_id}")
def get_company(company_id: str):
    """Full company detail: company info + vehicles + vehicle images + event tags."""
    db = get_client()

    company_result = (
        db.table("companies")
        .select("*")
        .eq("id", company_id)
        .limit(1)
        .execute()
    )
    if not company_result.data:
        raise HTTPException(status_code=404, detail="Company not found")

    company = company_result.data[0]

    # Vehicles
    vehicles_result = (
        db.table("vehicles")
        .select("*, vehicle_types(slug, label)")
        .eq("company_id", company_id)
        .execute()
    )
    company["vehicles"] = vehicles_result.data

    # Images
    images_result = (
        db.table("vehicle_images")
        .select("original_url, storage_path, detected_colors, is_primary")
        .eq("company_id", company_id)
        .limit(50)
        .execute()
    )
    company["images"] = images_result.data

    # Event tags
    tags_result = (
        db.table("company_event_tags")
        .select("event_types(slug, label), confidence, source")
        .eq("company_id", company_id)
        .execute()
    )
    company["event_tags"] = [
        {
            "slug": row["event_types"]["slug"],
            "label": row["event_types"]["label"],
            "confidence": row["confidence"],
            "source": row["source"],
        }
        for row in tags_result.data
    ]

    return company