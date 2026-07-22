"""
scraper/spiders/google_maps_spider.py
--------------------------------------
Discovers limo & party bus companies across the USA using the
Google Places API (Text Search + Place Details).

Run:
    python -m scraper.spiders.google_maps_spider --state TX
    python -m scraper.spiders.google_maps_spider --all-states
"""

from __future__ import annotations

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

import argparse
import logging
import time
from typing import Iterator

import httpx

from config.settings import get_settings
from scraper.utils.rate_limiter import RateLimiter
from scraper.utils.supabase_client import (
    get_company_by_url,
    start_scrape_log,
    finish_scrape_log,
    upsert_company,
)

logger = logging.getLogger(__name__)
settings = get_settings()

# All 50 US states + DC
US_STATES: list[tuple[str, str]] = [
    ("AL", "Alabama"), ("AK", "Alaska"), ("AZ", "Arizona"), ("AR", "Arkansas"),
    ("CA", "California"), ("CO", "Colorado"), ("CT", "Connecticut"), ("DE", "Delaware"),
    ("FL", "Florida"), ("GA", "Georgia"), ("HI", "Hawaii"), ("ID", "Idaho"),
    ("IL", "Illinois"), ("IN", "Indiana"), ("IA", "Iowa"), ("KS", "Kansas"),
    ("KY", "Kentucky"), ("LA", "Louisiana"), ("ME", "Maine"), ("MD", "Maryland"),
    ("MA", "Massachusetts"), ("MI", "Michigan"), ("MN", "Minnesota"), ("MS", "Mississippi"),
    ("MO", "Missouri"), ("MT", "Montana"), ("NE", "Nebraska"), ("NV", "Nevada"),
    ("NH", "New Hampshire"), ("NJ", "New Jersey"), ("NM", "New Mexico"), ("NY", "New York"),
    ("NC", "North Carolina"), ("ND", "North Dakota"), ("OH", "Ohio"), ("OK", "Oklahoma"),
    ("OR", "Oregon"), ("PA", "Pennsylvania"), ("RI", "Rhode Island"), ("SC", "South Carolina"),
    ("SD", "South Dakota"), ("TN", "Tennessee"), ("TX", "Texas"), ("UT", "Utah"),
    ("VT", "Vermont"), ("VA", "Virginia"), ("WA", "Washington"), ("WV", "West Virginia"),
    ("WI", "Wisconsin"), ("WY", "Wyoming"), ("DC", "Washington DC"),
]

SEARCH_QUERIES = [
    "limousine service",
    "party bus rental",
    "limo rental",
    "luxury transportation",
]

PLACES_TEXT_SEARCH_URL = "https://maps.googleapis.com/maps/api/place/textsearch/json"
PLACES_DETAILS_URL = "https://maps.googleapis.com/maps/api/place/details/json"


class GoogleMapsSpider:
    """
    Searches Google Places for limo/party-bus companies in each US state,
    fetches full Place Details, and upserts results into Supabase.
    """

    def __init__(self) -> None:
        self.api_key = settings.GOOGLE_MAPS_API_KEY
        self.client = httpx.Client(timeout=30)
        self.limiter = RateLimiter(
            min_delay=settings.SCRAPER_DELAY_MIN,
            max_delay=settings.SCRAPER_DELAY_MAX,
        )

    # ── Discovery ──────────────────────────────────────────────────────────

    def search_state(self, state_code: str, state_name: str) -> list[dict]:
        """Run all search queries for one state; deduplicate by place_id."""
        seen_place_ids: set[str] = set()
        all_places: list[dict] = []

        for query in SEARCH_QUERIES:
            full_query = f"{query} in {state_name}"
            logger.info("Searching: %s", full_query)

            places = self._paginated_text_search(full_query)
            for place in places:
                pid = place.get("place_id")
                if pid and pid not in seen_place_ids:
                    seen_place_ids.add(pid)
                    all_places.append(place)

        logger.info("State %s → %d unique places found", state_code, len(all_places))
        return all_places

    def _paginated_text_search(self, query: str) -> Iterator[dict]:
        """Yield places across up to 3 pages of Google Places results."""
        params = {
            "query": query,
            "type": "establishment",
            "key": self.api_key,
        }
        page = 0
        next_page_token = None

        while page < 3:
            if next_page_token:
                # Google requires a short delay before using a next_page_token
                time.sleep(2.0)
                params = {"pagetoken": next_page_token, "key": self.api_key}

            self.limiter.wait_sync()
            resp = self.client.get(PLACES_TEXT_SEARCH_URL, params=params)
            resp.raise_for_status()
            data = resp.json()

            if data.get("status") not in ("OK", "ZERO_RESULTS"):
                logger.warning("Places API error: %s", data.get("status"))
                break

            yield from data.get("results", [])

            next_page_token = data.get("next_page_token")
            if not next_page_token:
                break
            page += 1

    # ── Enrichment ─────────────────────────────────────────────────────────

    def fetch_place_details(self, place_id: str) -> dict:
        """Fetch full Place Details for a single place_id."""
        self.limiter.wait_sync()
        fields = ",".join([
            "name", "formatted_address", "formatted_phone_number",
            "website", "rating", "user_ratings_total",
            "opening_hours", "photos", "editorial_summary",
            "address_components",
        ])
        params = {"place_id": place_id, "fields": fields, "key": self.api_key}
        resp = self.client.get(PLACES_DETAILS_URL, params=params)
        resp.raise_for_status()
        return resp.json().get("result", {})

    # ── Transform ──────────────────────────────────────────────────────────

    @staticmethod
    def extract_state_from_components(components: list[dict]) -> str | None:
        for c in components:
            if "administrative_area_level_1" in c.get("types", []):
                return c.get("short_name")
        return None

    @staticmethod
    def extract_city_from_components(components: list[dict]) -> str | None:
        for c in components:
            if "locality" in c.get("types", []):
                return c.get("long_name")
        return None

    def to_company_row(self, place: dict, detail: dict, state_code: str) -> dict:
        components = detail.get("address_components", [])
        return {
            "name": detail.get("name") or place.get("name"),
            "url": detail.get("website", ""),
            "phone": detail.get("formatted_phone_number"),
            "address": detail.get("formatted_address"),
            "city": self.extract_city_from_components(components),
            "state": self.extract_state_from_components(components) or state_code,
            "description": detail.get("editorial_summary", {}).get("overview"),
            "rating": detail.get("rating"),
            "review_count": detail.get("user_ratings_total", 0),
            "last_scraped_at": "now()",
        }

    # ── Main Run ───────────────────────────────────────────────────────────

    def run(self, states: list[tuple[str, str]]) -> None:
        for state_code, state_name in states:
            log_id = start_scrape_log("google_maps_spider", state=state_code)
            found = new = updated = 0
            errors: list[str] = []

            try:
                places = self.search_state(state_code, state_name)
                found = len(places)

                for place in places:
                    try:
                        place_id = place.get("place_id")
                        if not place_id:
                            continue

                        detail = self.fetch_place_details(place_id)
                        url = detail.get("website", "")
                        if not url:
                            continue  # skip companies with no website

                        existing = get_company_by_url(url)
                        row = self.to_company_row(place, detail, state_code)
                        upsert_company(row)

                        if existing:
                            updated += 1
                        else:
                            new += 1

                    except Exception as exc:
                        msg = f"Error processing place {place.get('name')}: {exc}"
                        logger.error(msg)
                        errors.append(msg)

            except Exception as exc:
                msg = f"Fatal error for state {state_code}: {exc}"
                logger.error(msg)
                errors.append(msg)
                finish_scrape_log(
                    log_id, status="failed", companies_found=found,
                    companies_new=new, companies_updated=updated, errors=errors
                )
                continue

            finish_scrape_log(
                log_id, status="done", companies_found=found,
                companies_new=new, companies_updated=updated, errors=errors
            )
            logger.info(
                "State %s done: %d found, %d new, %d updated",
                state_code, found, new, updated
            )


# ── CLI ───────────────────────────────────────────────────────────────────────

def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Google Maps Limo Spider")
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--all-states", action="store_true", help="Scrape all 50 US states")
    group.add_argument("--state", metavar="CODE", help="Two-letter state code, e.g. TX")
    return parser.parse_args()


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")
    args = parse_args()

    if args.all_states:
        target_states = US_STATES
    else:
        code = args.state.upper()
        target_states = [(c, n) for c, n in US_STATES if c == code]
        if not target_states:
            raise SystemExit(f"Unknown state code: {code}")

    spider = GoogleMapsSpider()
    spider.run(target_states)
