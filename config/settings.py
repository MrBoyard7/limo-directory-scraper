"""
config/settings.py
------------------
Centralized configuration loaded from environment variables.
Copy .env.example → .env and fill in your credentials.
"""

from functools import lru_cache
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    # ── Supabase ──────────────────────────────────────────────
    SUPABASE_URL: str
    SUPABASE_KEY: str  # anon or service_role key
    SUPABASE_STORAGE_BUCKET: str = "vehicle-images"

    # ── Google Maps / Places API ──────────────────────────────
    GOOGLE_MAPS_API_KEY: str
    GOOGLE_PLACES_MAX_RESULTS: int = 60  # max per state (20 per page × 3 pages)

    # ── Scraping behaviour ────────────────────────────────────
    SCRAPER_DELAY_MIN: float = 1.5  # seconds between requests (min)
    SCRAPER_DELAY_MAX: float = 3.5  # seconds between requests (max)
    SCRAPER_TIMEOUT: int = 30  # page load timeout (seconds)
    SCRAPER_MAX_RETRIES: int = 3
    USE_PROXIES: bool = False
    PROXY_LIST_PATH: str = "config/proxies.txt"

    # ── Color detection ───────────────────────────────────────
    COLOR_DETECTION_ENABLED: bool = True
    COLOR_KMEANS_CLUSTERS: int = 5
    COLOR_MIN_CONFIDENCE: float = 0.30  # ignore colors below this threshold
    COLOR_RESIZE_PX: int = 150  # resize images to NxN before analysis

    # ── API ───────────────────────────────────────────────────
    API_HOST: str = "0.0.0.0"
    API_PORT: int = 8000
    API_DEFAULT_PAGE_SIZE: int = 25
    API_MAX_PAGE_SIZE: int = 100

    # ── Notifications ─────────────────────────────────────────
    SLACK_WEBHOOK_URL: str = ""  # optional Slack notification on run end

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")


@lru_cache()
def get_settings() -> Settings:
    """Return cached settings singleton."""
    return Settings()  # type: ignore[call-arg]
