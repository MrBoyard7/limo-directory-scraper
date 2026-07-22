"""
api/routers/directories.py
---------------------------
GET /directories         → all available directories
GET /directories/{slug}  → one directory + its matching companies
"""

from __future__ import annotations

from typing import Annotated
from fastapi import APIRouter, HTTPException, Query

from scraper.utils.supabase_client import get_client
from config.settings import get_settings

router = APIRouter()
settings = get_settings()


@router.get("")
def list_directories():
    """Return all active niche directories."""
    db = get_client()
    result = (
        db.table("directories")
        .select("slug, title, description, meta_title, meta_description")
        .eq("is_active", True)
        .order("title")
        .execute()
    )
    return result.data


@router.get("/{slug}")
def get_directory(
    slug: str,
    state: Annotated[str | None, Query(description="Filter by state code")] = None,
    page: Annotated[int, Query(ge=1)] = 1,
    limit: Annotated[int, Query(ge=1, le=100)] = settings.API_DEFAULT_PAGE_SIZE,
):
    """
    Resolve a directory by slug and return its matching companies.
    The filter_config column drives the query against v_companies_enriched.
    """
    db = get_client()

    # Load directory config
    dir_result = (
        db.table("directories")
        .select("*")
        .eq("slug", slug)
        .eq("is_active", True)
        .limit(1)
        .execute()
    )
    if not dir_result.data:
        raise HTTPException(status_code=404, detail=f"Directory '{slug}' not found")

    directory = dir_result.data[0]
    filter_config: dict = directory.get("filter_config") or {}

    # Build query
    query = db.table("v_companies_enriched").select("*")

    vehicle_color = filter_config.get("vehicle_color")
    vehicle_type_slugs = filter_config.get("vehicle_type_slugs", [])
    event_type_slugs = filter_config.get("event_type_slugs", [])

    if vehicle_color:
        query = query.contains("vehicle_colors", [vehicle_color])

    # For vehicle types: match if company has ANY of the listed types
    # Supabase overlaps operator: cs (contains) vs. ov (overlaps)
    # We'll use 'overlaps' for multi-value slug lists
    if vehicle_type_slugs:
        query = query.overlaps("vehicle_type_slugs", vehicle_type_slugs)

    if event_type_slugs:
        query = query.overlaps("event_type_slugs", event_type_slugs)

    if state:
        query = query.eq("state", state.upper())

    offset = (page - 1) * limit
    result = query.range(offset, offset + limit - 1).execute()

    return {
        "directory": {
            "slug": directory["slug"],
            "title": directory["title"],
            "description": directory["description"],
            "meta_title": directory["meta_title"],
            "meta_description": directory["meta_description"],
        },
        "page": page,
        "limit": limit,
        "count": len(result.data),
        "companies": result.data,
    }
