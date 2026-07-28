"""
scraper/processors/color_detector.py
--------------------------------------
Downloads vehicle images and uses KMeans clustering to detect
the dominant color(s). Updates the vehicle_images table with
detected_colors (JSON array with confidence scores).

Run:
    python -m scraper.processors.color_detector
    python -m scraper.processors.color_detector --limit 500
"""

from __future__ import annotations

import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

import argparse
import io
import json
import logging
from typing import NamedTuple

import httpx
import numpy as np
from PIL import Image
from sklearn.cluster import KMeans

from config.settings import get_settings
from scraper.utils.supabase_client import get_client
from scraper.utils.rate_limiter import RateLimiter

logger = logging.getLogger(__name__)
settings = get_settings()


# ── Color name mapping ─────────────────────────────────────────────────────────


class ColorRange(NamedTuple):
    name: str
    h_min: float  # HSV hue min (0–360)
    h_max: float
    s_min: float  # saturation min (0–1)
    v_min: float  # value/brightness min (0–1)


# Ordered from most specific to most general
COLOR_RANGES: list[ColorRange] = [
    ColorRange("red", 0, 15, 0.40, 0.30),
    ColorRange("red", 345, 360, 0.40, 0.30),
    ColorRange("pink", 300, 345, 0.25, 0.50),
    ColorRange("orange", 15, 40, 0.45, 0.40),
    ColorRange("yellow", 40, 65, 0.40, 0.60),
    ColorRange("green", 65, 150, 0.25, 0.20),
    ColorRange("blue", 150, 260, 0.25, 0.20),
    ColorRange("purple", 260, 300, 0.20, 0.20),
    ColorRange("gold", 30, 50, 0.50, 0.40),
]

NEUTRAL_MAP = [
    ("white", {"v_min": 0.85, "s_max": 0.12}),
    ("silver", {"v_min": 0.55, "s_max": 0.12}),
    ("black", {"v_max": 0.25}),
    ("gray", {"s_max": 0.15}),
    ("champagne", {"v_min": 0.75, "s_min": 0.08, "s_max": 0.25, "h_min": 25, "h_max": 55}),
]


def rgb_to_hsv(r: float, g: float, b: float) -> tuple[float, float, float]:
    """Convert RGB [0,1] to HSV: H [0,360], S [0,1], V [0,1]."""
    max_c = max(r, g, b)
    min_c = min(r, g, b)
    delta = max_c - min_c

    v = max_c
    s = delta / max_c if max_c > 0 else 0.0

    if delta == 0:
        h = 0.0
    elif max_c == r:
        h = 60 * (((g - b) / delta) % 6)
    elif max_c == g:
        h = 60 * (((b - r) / delta) + 2)
    else:
        h = 60 * (((r - g) / delta) + 4)

    return h, s, v


def classify_color(r: int, g: int, b: int) -> str:
    """Map an RGB triplet to a human-readable color name."""
    h, s, v = rgb_to_hsv(r / 255, g / 255, b / 255)

    # Check neutrals first
    if v >= 0.85 and s <= 0.12:
        return "white"
    if v <= 0.25:
        return "black"
    if s <= 0.12:
        return "silver" if v >= 0.55 else "gray"
    if 25 <= h <= 55 and 0.08 <= s <= 0.25 and v >= 0.75:
        return "champagne"

    # Check hue-based colors
    for cr in COLOR_RANGES:
        in_hue = (cr.h_min <= h <= cr.h_max) or (
            cr.h_min > cr.h_max and (h >= cr.h_min or h <= cr.h_max)
        )
        if in_hue and s >= cr.s_min and v >= cr.v_min:
            return cr.name

    return "other"


# ── Image processing ───────────────────────────────────────────────────────────


def detect_colors_from_image(image_bytes: bytes) -> list[dict]:
    """
    Returns a list of {"color": str, "confidence": float} sorted by confidence desc.
    Only includes colors above settings.COLOR_MIN_CONFIDENCE.
    """
    try:
        img = Image.open(io.BytesIO(image_bytes)).convert("RGB")
    except Exception as exc:
        logger.warning("Cannot open image: %s", exc)
        return []

    size = settings.COLOR_RESIZE_PX
    img = img.resize((size, size))
    pixels = np.array(img).reshape(-1, 3)

    # Remove near-white background pixels (common in website renders)
    not_background = ~((pixels[:, 0] > 240) & (pixels[:, 1] > 240) & (pixels[:, 2] > 240))
    pixels = pixels[not_background]
    if len(pixels) < 50:
        pixels = np.array(img).reshape(-1, 3)  # fallback: use all pixels

    k = min(settings.COLOR_KMEANS_CLUSTERS, len(pixels))
    kmeans = KMeans(n_clusters=k, n_init=10, random_state=42)
    kmeans.fit(pixels)

    centers = kmeans.cluster_centers_.astype(int)
    labels = kmeans.labels_
    total = len(labels)

    color_counts: dict[str, int] = {}
    for idx, center in enumerate(centers):
        name = classify_color(*center)
        count = int(np.sum(labels == idx))
        color_counts[name] = color_counts.get(name, 0) + count

    results = [
        {"color": name, "confidence": round(count / total, 3)}
        for name, count in sorted(color_counts.items(), key=lambda x: x[1], reverse=True)
        if count / total >= settings.COLOR_MIN_CONFIDENCE and name not in ("other", "gray")
    ]
    return results


# ── Processor ──────────────────────────────────────────────────────────────────


class ColorDetector:
    """
    Fetches unprocessed vehicle images from Supabase,
    runs color detection, and saves results back.
    """

    def __init__(self) -> None:
        self.supabase = get_client()
        self.http = httpx.Client(timeout=20, follow_redirects=True)
        self.limiter = RateLimiter(
            min_delay=settings.SCRAPER_DELAY_MIN,
            max_delay=settings.SCRAPER_DELAY_MAX,
        )

    def fetch_unprocessed(self, limit: int) -> list[dict]:
        result = (
            self.supabase.table("vehicle_images")
            .select("id, vehicle_id, company_id, original_url")
            .eq("detected_colors", "[]")
            .limit(limit)
            .execute()
        )
        return result.data

    def download_image(self, url: str) -> bytes | None:
        self.limiter.wait_sync()
        try:
            resp = self.http.get(url)
            resp.raise_for_status()
            return resp.content
        except Exception as exc:
            logger.warning("Download failed %s: %s", url, exc)
            return None

    def update_image_colors(self, image_id: str, detected: list[dict]) -> None:
        self.supabase.table("vehicle_images").update({"detected_colors": json.dumps(detected)}).eq(
            "id", image_id
        ).execute()

    def update_vehicle_primary_color(self, vehicle_id: str | None, color: str) -> None:
        if not vehicle_id:
            return
        # Only update if vehicle has no primary color yet
        existing = (
            self.supabase.table("vehicles")
            .select("primary_color")
            .eq("id", vehicle_id)
            .limit(1)
            .execute()
        )
        if existing.data and not existing.data[0].get("primary_color"):
            self.supabase.table("vehicles").update({"primary_color": color}).eq(
                "id", vehicle_id
            ).execute()

    def run(self, limit: int = 1000) -> None:
        images = self.fetch_unprocessed(limit)
        logger.info("Processing %d images for color detection", len(images))

        processed = skipped = failed = 0
        for img_row in images:
            image_bytes = self.download_image(img_row["original_url"])
            if not image_bytes:
                skipped += 1
                continue

            detected = detect_colors_from_image(image_bytes)
            if not detected:
                skipped += 1
                continue

            self.update_image_colors(img_row["id"], detected)

            top_color = detected[0]["color"]
            self.update_vehicle_primary_color(img_row.get("vehicle_id"), top_color)

            processed += 1
            logger.debug("Image %s → %s", img_row["original_url"], detected)

        logger.info(
            "Color detection done: %d processed, %d skipped, %d failed",
            processed,
            skipped,
            failed,
        )


# ── CLI ───────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")
    parser = argparse.ArgumentParser()
    parser.add_argument("--limit", type=int, default=1000)
    args = parser.parse_args()
    ColorDetector().run(limit=args.limit)
