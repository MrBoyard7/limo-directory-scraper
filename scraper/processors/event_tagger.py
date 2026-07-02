"""
scraper/processors/event_tagger.py
------------------------------------
Tags companies with event types (wedding, prom, bachelorette, etc.)
using keyword matching against company description + website text.

Run:
    python -m scraper.processors.event_tagger
    python -m scraper.processors.event_tagger --limit 500
"""

from __future__ import annotations

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

import argparse
import logging

from config.settings import get_settings
from scraper.utils.supabase_client import get_client, tag_company_events

logger = logging.getLogger(__name__)
settings = get_settings()

# ── Keyword rules ──────────────────────────────────────────────────────────────
# Each entry: event_slug → list of trigger keywords (any match = tagged)

EVENT_KEYWORD_MAP: dict[str, list[str]] = {
    "wedding": [
        "wedding", "bride", "bridal", "groom", "ceremony", "reception",
        "vow", "honeymoon", "just married", "nuptial",
    ],
    "prom": [
        "prom", "homecoming", "high school dance", "prom night",
        "prom transportation", "prom limo",
    ],
    "birthday": [
        "birthday", "sweet 16", "sweet sixteen", "quinceañera", "quinceanera",
        "milestone birthday", "birthday party",
    ],
    "bachelorette": [
        "bachelorette", "bachelorette party", "girls night out",
        "ladies night", "hen party", "last night of freedom",
    ],
    "bachelor": [
        "bachelor", "bachelor party", "stag night", "stag party", "guys night",
    ],
    "corporate": [
        "corporate", "business travel", "executive", "roadshow", "conference",
        "client transportation", "vip transfer", "business event",
    ],
    "airport": [
        "airport", "airport transfer", "airport pickup", "airport shuttle",
        "airport transportation", "airport limo", "flight",
    ],
    "concert": [
        "concert", "show", "music festival", "sports event", "game day",
        "stadium", "theater", "nightclub", "club crawl", "bar hop",
    ],
    "quinceañera": [
        "quinceañera", "quinceanera", "quinces", "sweet 15", "fifteenth birthday",
    ],
    "wine_tour": [
        "wine tour", "winery tour", "vineyard", "wine country", "wine tasting",
    ],
    "brewery_tour": [
        "brewery tour", "brewery hop", "bar crawl", "pub crawl", "distillery",
    ],
    "sightseeing": [
        "sightseeing", "city tour", "guided tour", "tourist", "landmark tour",
    ],
    "funeral": [
        "funeral", "memorial service", "graveside", "bereavement",
    ],
}


def tag_company(company: dict) -> list[str]:
    """
    Given a company dict (with name + description), return matching event slugs.
    """
    text = " ".join([
        company.get("name") or "",
        company.get("description") or "",
    ]).lower()

    matched: list[str] = []
    for event_slug, keywords in EVENT_KEYWORD_MAP.items():
        if any(kw in text for kw in keywords):
            matched.append(event_slug)

    return matched


# ── Processor ──────────────────────────────────────────────────────────────────

class EventTagger:
    def __init__(self) -> None:
        self.supabase = get_client()

    def fetch_untagged(self, limit: int) -> list[dict]:
        """
        Returns companies that have no event tags yet.
        Joins to company_event_tags and filters by absence.
        """
        # Use a simple approach: fetch all companies and exclude those
        # that already appear in company_event_tags
        tagged_result = (
            self.supabase.table("company_event_tags")
            .select("company_id")
            .execute()
        )
        tagged_ids = {row["company_id"] for row in (tagged_result.data or [])}

        all_result = (
            self.supabase.table("companies")
            .select("id, name, description")
            .limit(limit * 3)  # fetch extra to account for already-tagged ones
            .execute()
        )
        untagged = [c for c in (all_result.data or []) if c["id"] not in tagged_ids]
        return untagged[:limit]

    def run(self, limit: int = 500) -> None:
        companies = self.fetch_untagged(limit)
        logger.info("Tagging %d companies with event types", len(companies))

        total_tags = 0
        for company in companies:
            event_slugs = tag_company(company)
            if event_slugs:
                tag_company_events(company["id"], event_slugs, source="keyword")
                total_tags += len(event_slugs)
                logger.debug("%s → %s", company["name"], event_slugs)

        logger.info("Event tagging done. %d total tags applied.", total_tags)


# ── CLI ───────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")
    parser = argparse.ArgumentParser()
    parser.add_argument("--limit", type=int, default=500)
    args = parser.parse_args()
    EventTagger().run(limit=args.limit)