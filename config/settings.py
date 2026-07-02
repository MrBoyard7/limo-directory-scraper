from functools import lru_cache
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    SUPABASE_URL: str = ""
    SUPABASE_KEY: str = ""
    SUPABASE_STORAGE_BUCKET: str = "vehicle-images"
    GOOGLE_MAPS_API_KEY: str = ""
    SCRAPER_DELAY_MIN: float = 1.5
    SCRAPER_DELAY_MAX: float = 3.5
    SCRAPER_TIMEOUT: int = 30
    SCRAPER_MAX_RETRIES: int = 3
    USE_PROXIES: bool = False
    COLOR_DETECTION_ENABLED: bool = True
    COLOR_KMEANS_CLUSTERS: int = 5
    COLOR_MIN_CONFIDENCE: float = 0.30
    COLOR_RESIZE_PX: int = 150
    API_HOST: str = "0.0.0.0"
    API_PORT: int = 8000
    API_DEFAULT_PAGE_SIZE: int = 25
    API_MAX_PAGE_SIZE: int = 100
    SLACK_WEBHOOK_URL: str = ""

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")


@lru_cache()
def get_settings() -> Settings:
    return Settings()