"""
scraper/spiders/company_spider.py
----------------------------------
Uses Playwright (headless Chromium) to scrape individual company websites.
Extracts: email, vehicle descriptions, amenities, and image URLs.

Run:
    python -m scraper.spiders.company_spider          # process all unscraped
    python -m scraper.spiders.company_spider --limit 10
"""

from __future__ import annotations

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

import argparse
import asyncio
import logging
import re
from urllib.parse import urljoin, urlparse

from playwright.async_api import async_playwright, Page, Browser

from config.settings import get_settings
from scraper.utils.supabase_client import get_client, upsert_company, insert_vehicle

logger = logging.getLogger(__name__)
settings = get_settings()

# ── Keyword lists ─────────────────────────────────────────────────────────────

VEHICLE_TYPE_KEYWORDS: dict[str, list[str]] = {
    "stretch_limo":  ["stretch limo", "stretch limousine", "classic limo"],
    "suv_limo":      ["suv limo", "suv limousine", "navigator limo", "escalade limo"],
    "hummer_limo":   ["hummer limo", "hummer limousine"],
    "party_bus":     ["party bus", "party coach"],
    "mini_bus":      ["mini bus", "minibus", "mini coach"],
    "sprinter_van":  ["sprinter van", "sprinter limo", "mercedes sprinter"],
    "sedan":         ["luxury sedan", "town car", "lincoln town car", "cadillac sedan"],
    "vintage":       ["vintage", "classic car", "antique limo", "rolls royce"],
    "trolley":       ["trolley"],
    "double_decker": ["double decker", "double-decker"],
}

COLOR_KEYWORDS: dict[str, list[str]] = {
    "black":   ["black"],
    "white":   ["white"],
    "red":     ["red"],
    "silver":  ["silver", "champagne", "platinum"],
    "gold":    ["gold", "golden"],
    "pink":    ["pink", "hot pink"],
    "blue":    ["blue", "cobalt", "navy"],
    "purple":  ["purple", "violet", "lavender"],
    "green":   ["green", "emerald"],
    "yellow":  ["yellow", "canary"],
}

AMENITY_KEYWORDS = [
    "bar", "mini bar", "wet bar", "led lights", "fiber optic", "tv", "television",
    "dvd", "bluetooth", "wifi", "wi-fi", "karaoke", "dance floor", "stripper pole",
    "laser lights", "fog machine", "leather seats", "leather interior",
    "privacy partition", "sunroof", "moon roof", "ice chest", "cooler",
    "surround sound", "custom sound system",
]

EMAIL_PATTERN = re.compile(r"[a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,}")
CAPACITY_PATTERN = re.compile(r"(\d{1,3})\s*(?:-\s*\d{1,3})?\s*(?:passenger|person|people|pax)", re.I)


class CompanySpider:
    """Playwright-based spider for company websites."""

    def __init__(self) -> None:
        self.supabase = get_client()

    # ── Extraction helpers ─────────────────────────────────────────────────

    @staticmethod
    def extract_emails(text: str) -> list[str]:
        return list(set(EMAIL_PATTERN.findall(text)))

    @staticmethod
    def detect_vehicle_types(text: str) -> list[str]:
        text_lower = text.lower()
        found = []
        for vtype, keywords in VEHICLE_TYPE_KEYWORDS.items():
            if any(kw in text_lower for kw in keywords):
                found.append(vtype)
        return found

    @staticmethod
    def detect_colors(text: str) -> list[str]:
        text_lower = text.lower()
        found = []
        for color, keywords in COLOR_KEYWORDS.items():
            if any(kw in text_lower for kw in keywords):
                found.append(color)
        return found

    @staticmethod
    def detect_amenities(text: str) -> list[str]:
        text_lower = text.lower()
        return [a for a in AMENITY_KEYWORDS if a in text_lower]

    @staticmethod
    def detect_capacity(text: str) -> int | None:
        match = CAPACITY_PATTERN.search(text)
        return int(match.group(1)) if match else None

    @staticmethod
    async def extract_image_urls(page: Page, base_url: str) -> list[str]:
        """Collect all <img> src attributes that look like vehicle photos."""
        img_handles = await page.query_selector_all("img")
        urls: list[str] = []
        for img in img_handles:
            src = await img.get_attribute("src") or ""
            src = src.strip()
            if not src or src.startswith("data:") or "logo" in src.lower():
                continue
            full_url = src if src.startswith("http") else urljoin(base_url, src)
            urls.append(full_url)
        return list(dict.fromkeys(urls))  # deduplicate while preserving order

    # ── Page scraping ──────────────────────────────────────────────────────

    async def scrape_page(self, page: Page, url: str) -> dict:
        """Scrape a single URL and return extracted data."""
        try:
            await page.goto(url, wait_until="domcontentloaded", timeout=settings.SCRAPER_TIMEOUT * 1000)
            await page.wait_for_timeout(1500)   # let JS render
        except Exception as exc:
            logger.warning("Failed to load %s: %s", url, exc)
            return {}

        text = await page.inner_text("body")
        image_urls = await self.extract_image_urls(page, url)

        return {
            "emails":       self.extract_emails(text),
            "vehicle_types": self.detect_vehicle_types(text),
            "colors":       self.detect_colors(text),
            "amenities":    self.detect_amenities(text),
            "capacity":     self.detect_capacity(text),
            "image_urls":   image_urls,
            "raw_text":     text[:5000],  # store snippet for debugging
        }

    # ── Main scrape loop ───────────────────────────────────────────────────

    async def run(self, limit: int = 100) -> None:
        # Fetch companies that have a URL but haven't been deep-scraped recently
        result = (
            self.supabase.table("companies")
            .select("id, name, url")
            .not_.is_("url", "null")
            .order("last_scraped_at", desc=False, nullsfirst=True)
            .limit(limit)
            .execute()
        )
        companies = result.data
        logger.info("Processing %d companies", len(companies))

        async with async_playwright() as pw:
            browser: Browser = await pw.chromium.launch(headless=True)
            context = await browser.new_context(
                user_agent=(
                    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                    "AppleWebKit/537.36 (KHTML, like Gecko) "
                    "Chrome/124.0.0.0 Safari/537.36"
                )
            )
            page = await context.new_page()

            for company in companies:
                url = company["url"]
                name = company["name"]
                company_id = company["id"]

                logger.info("Scraping: %s (%s)", name, url)
                data = await self.scrape_page(page, url)

                if not data:
                    continue

                # Update company with email
                if data["emails"]:
                    upsert_company({"url": url, "email": data["emails"][0], "last_scraped_at": "now()"})

                # Create a vehicle row per detected type
                for vtype in data["vehicle_types"] or ["stretch_limo"]:
                    vehicle_row = {
                        "company_id": company_id,
                        "description": data["raw_text"][:500],
                        "primary_color": data["colors"][0] if data["colors"] else None,
                        "amenities": data["amenities"],
                        "capacity": data["capacity"],
                    }
                    try:
                        # Resolve vehicle type slug → id
                        vt_result = (
                            self.supabase.table("vehicle_types")
                            .select("id")
                            .eq("slug", vtype)
                            .limit(1)
                            .execute()
                        )
                        if vt_result.data:
                            vehicle_row["vehicle_type_id"] = vt_result.data[0]["id"]
                        insert_vehicle(vehicle_row)
                    except Exception as exc:
                        logger.warning("Could not insert vehicle for %s: %s", name, exc)

                # Store image URLs in vehicle_images
                for img_url in data["image_urls"][:20]:  # cap at 20 images
                    try:
                        self.supabase.table("vehicle_images").upsert(
                            {"company_id": company_id, "original_url": img_url},
                            on_conflict="original_url",
                        ).execute()
                    except Exception:
                        pass

                await asyncio.sleep(settings.SCRAPER_DELAY_MIN)

            await browser.close()

        logger.info("Company spider done.")


# ── CLI ───────────────────────────────────────────────────────────────────────

def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Company Website Spider")
    parser.add_argument("--limit", type=int, default=100, help="Max companies to process")
    return parser.parse_args()


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")
    args = parse_args()
    asyncio.run(CompanySpider().run(limit=args.limit))
