"""
api/main.py
-----------
FastAPI application entrypoint.

Run:
    uvicorn api.main:app --reload
    → http://localhost:8000/docs
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from api.routers import companies, directories, vehicles

app = FastAPI(
    title="Limo & Party Bus Directory API",
    description=(
        "REST API powering niche limo and party bus directories across the USA. "
        "Filter by vehicle color, event type, state, and more."
    ),
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
)

# ── CORS ──────────────────────────────────────────────────────────────────────
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # tighten in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Routers ───────────────────────────────────────────────────────────────────
app.include_router(companies.router, prefix="/companies", tags=["Companies"])
app.include_router(vehicles.router, prefix="/vehicles", tags=["Vehicles"])
app.include_router(directories.router, prefix="/directories", tags=["Directories"])


@app.get("/", tags=["Health"])
def root():
    return {"status": "ok", "message": "Limo Directory API is running 🚗"}


@app.get("/stats", tags=["Health"])
def stats():
    """High-level scraping statistics."""
    from scraper.utils.supabase_client import get_client

    db = get_client()

    companies_count = db.table("companies").select("id", count="exact").execute().count
    vehicles_count = db.table("vehicles").select("id", count="exact").execute().count
    images_count = db.table("vehicle_images").select("id", count="exact").execute().count

    return {
        "companies_total": companies_count,
        "vehicles_total": vehicles_count,
        "images_total": images_count,
    }
