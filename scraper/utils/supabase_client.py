"""
scraper/utils/supabase_client.py
---------------------------------
Thin wrapper around supabase-py.
Handles upserts, batch inserts, and image storage uploads.
"""

from __future__ import annotations

import logging
from typing import Any

from supabase import Client, create_client

from config.settings import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()

# Singleton client
_client: Client | None = None


def get_client() -> Client:
    global _client
    if _client is None:
        _client = create_client(settings.SUPABASE_URL, settings.SUPABASE_KEY)
    return _client


# ── Companies ─────────────────────────────────────────────────────────────────

def upsert_company(data: dict[str, Any]) -> dict[str, Any]:
    """
    Insert or update a company by URL (unique key).
    Returns the full row including the assigned UUID.
    """
    client = get_client()
    result = (
        client.table("companies")
        .upsert(data, on_conflict="url")
        .execute()
    )
    row = result.data[0]
    logger.info("Upserted company: %s → id=%s", data.get("name"), row["id"])
    return row


def get_company_by_url(url: str) -> dict[str, Any] | None:
    client = get_client()
    result = (
        client.table("companies")
        .select("*")
        .eq("url", url)
        .limit(1)
        .execute()
    )
    return result.data[0] if result.data else None


# ── Vehicles ──────────────────────────────────────────────────────────────────

def insert_vehicle(data: dict[str, Any]) -> dict[str, Any]:
    client = get_client()
    result = client.table("vehicles").insert(data).execute()
    return result.data[0]


def upsert_vehicle_image(data: dict[str, Any]) -> dict[str, Any]:
    client = get_client()
    result = (
        client.table("vehicle_images")
        .upsert(data, on_conflict="original_url")
        .execute()
    )
    return result.data[0]


# ── Event Tags ────────────────────────────────────────────────────────────────

def tag_company_events(company_id: str, event_slugs: list[str], source: str = "ml") -> None:
    """
    Resolve event type slugs → IDs, then upsert into company_event_tags.
    """
    client = get_client()
    if not event_slugs:
        return

    # Resolve slugs → IDs
    result = (
        client.table("event_types")
        .select("id, slug")
        .in_("slug", event_slugs)
        .execute()
    )
    for row in result.data:
        client.table("company_event_tags").upsert(
            {"company_id": company_id, "event_type_id": row["id"], "source": source},
            on_conflict="company_id,event_type_id",
        ).execute()

    logger.info("Tagged company %s with events: %s", company_id, event_slugs)


# ── Scrape Logs ───────────────────────────────────────────────────────────────

def start_scrape_log(spider_name: str, state: str | None = None) -> int:
    client = get_client()
    result = (
        client.table("scrape_logs")
        .insert({"spider_name": spider_name, "state": state, "status": "running"})
        .execute()
    )
    return result.data[0]["id"]


def finish_scrape_log(
    log_id: int,
    *,
    status: str = "done",
    companies_found: int = 0,
    companies_new: int = 0,
    companies_updated: int = 0,
    errors: list[str] | None = None,
) -> None:
    client = get_client()
    client.table("scrape_logs").update(
        {
            "status": status,
            "companies_found": companies_found,
            "companies_new": companies_new,
            "companies_updated": companies_updated,
            "errors": errors or [],
            "finished_at": "now()",
        }
    ).eq("id", log_id).execute()


# ── Image Storage ─────────────────────────────────────────────────────────────

def upload_image_to_storage(image_bytes: bytes, path: str, content_type: str = "image/jpeg") -> str:
    """
    Upload raw image bytes to Supabase Storage.
    Returns the public URL.
    """
    client = get_client()
    bucket = settings.SUPABASE_STORAGE_BUCKET

    client.storage.from_(bucket).upload(
        path=path,
        file=image_bytes,
        file_options={"content-type": content_type},
    )
    public_url = client.storage.from_(bucket).get_public_url(path)
    return public_url