-- ============================================================
-- Migration 001: Initial Schema
-- Limo & Party Bus Directory Scraper
-- ============================================================

-- Enable UUID extension
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- ============================================================
-- COMPANIES
-- ============================================================
CREATE TABLE companies (
    id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    name            TEXT NOT NULL,
    url             TEXT UNIQUE NOT NULL,
    phone           TEXT,
    email           TEXT,
    address         TEXT,
    city            TEXT,
    state           CHAR(2),
    zip_code        TEXT,
    description     TEXT,
    logo_url        TEXT,
    rating          NUMERIC(2,1),
    review_count    INTEGER DEFAULT 0,
    years_in_business INTEGER,
    is_verified     BOOLEAN DEFAULT FALSE,
    last_scraped_at TIMESTAMPTZ,
    created_at      TIMESTAMPTZ DEFAULT NOW(),
    updated_at      TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_companies_state   ON companies(state);
CREATE INDEX idx_companies_city    ON companies(city);
CREATE INDEX idx_companies_url     ON companies(url);

-- ============================================================
-- VEHICLE TYPES (lookup)
-- ============================================================
CREATE TABLE vehicle_types (
    id      SERIAL PRIMARY KEY,
    slug    TEXT UNIQUE NOT NULL,   -- 'stretch_limo', 'party_bus', 'suv_limo' …
    label   TEXT NOT NULL           -- 'Stretch Limousine', 'Party Bus' …
);

INSERT INTO vehicle_types (slug, label) VALUES
    ('stretch_limo',   'Stretch Limousine'),
    ('suv_limo',       'SUV Limousine'),
    ('party_bus',      'Party Bus'),
    ('mini_bus',       'Mini Bus'),
    ('sedan',          'Luxury Sedan'),
    ('sprinter_van',   'Sprinter Van'),
    ('vintage',        'Vintage / Classic'),
    ('hummer_limo',    'Hummer Limousine'),
    ('double_decker',  'Double Decker Bus'),
    ('trolley',        'Trolley');

-- ============================================================
-- VEHICLES
-- ============================================================
CREATE TABLE vehicles (
    id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    company_id      UUID NOT NULL REFERENCES companies(id) ON DELETE CASCADE,
    vehicle_type_id INTEGER REFERENCES vehicle_types(id),
    name            TEXT,               -- e.g. "Our 20-passenger Hummer"
    description     TEXT,
    capacity        INTEGER,            -- max passengers
    year            INTEGER,
    make            TEXT,               -- Lincoln, Cadillac …
    model           TEXT,
    primary_color   TEXT,               -- 'red', 'black', 'white', 'silver' …
    secondary_color TEXT,
    amenities       JSONB DEFAULT '[]', -- ["LED lights","bar","TV","Bluetooth"]
    price_per_hour  NUMERIC(8,2),
    price_per_day   NUMERIC(8,2),
    created_at      TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_vehicles_company    ON vehicles(company_id);
CREATE INDEX idx_vehicles_color      ON vehicles(primary_color);
CREATE INDEX idx_vehicles_type       ON vehicles(vehicle_type_id);
CREATE INDEX idx_vehicles_capacity   ON vehicles(capacity);

-- ============================================================
-- VEHICLE IMAGES
-- ============================================================
CREATE TABLE vehicle_images (
    id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    vehicle_id      UUID NOT NULL REFERENCES vehicles(id) ON DELETE CASCADE,
    company_id      UUID NOT NULL REFERENCES companies(id) ON DELETE CASCADE,
    original_url    TEXT NOT NULL,
    storage_path    TEXT,               -- Supabase Storage path
    detected_colors JSONB DEFAULT '[]', -- [{"color":"red","confidence":0.87}]
    is_primary      BOOLEAN DEFAULT FALSE,
    width           INTEGER,
    height          INTEGER,
    created_at      TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_images_vehicle  ON vehicle_images(vehicle_id);
CREATE INDEX idx_images_company  ON vehicle_images(company_id);

-- ============================================================
-- EVENT TYPES (lookup)
-- ============================================================
CREATE TABLE event_types (
    id      SERIAL PRIMARY KEY,
    slug    TEXT UNIQUE NOT NULL,
    label   TEXT NOT NULL
);

INSERT INTO event_types (slug, label) VALUES
    ('wedding',         'Wedding'),
    ('prom',            'Prom / Homecoming'),
    ('birthday',        'Birthday Party'),
    ('bachelorette',    'Bachelorette Party'),
    ('bachelor',        'Bachelor Party'),
    ('corporate',       'Corporate Event'),
    ('airport',         'Airport Transfer'),
    ('concert',         'Concert / Show'),
    ('quinceañera',     'Quinceañera'),
    ('funeral',         'Funeral Service'),
    ('wine_tour',       'Wine Tour'),
    ('brewery_tour',    'Brewery Tour'),
    ('sightseeing',     'Sightseeing Tour');

-- ============================================================
-- COMPANY ↔ EVENT TAGS  (many-to-many)
-- ============================================================
CREATE TABLE company_event_tags (
    company_id    UUID NOT NULL REFERENCES companies(id) ON DELETE CASCADE,
    event_type_id INTEGER NOT NULL REFERENCES event_types(id),
    confidence    NUMERIC(3,2) DEFAULT 1.0,  -- 0.0 – 1.0 (ML confidence)
    source        TEXT DEFAULT 'manual',      -- 'manual' | 'ml' | 'keyword'
    PRIMARY KEY (company_id, event_type_id)
);

-- ============================================================
-- DIRECTORIES  (niche directories config)
-- ============================================================
CREATE TABLE directories (
    id              SERIAL PRIMARY KEY,
    slug            TEXT UNIQUE NOT NULL,   -- 'red-limos'
    title           TEXT NOT NULL,          -- 'Red Limousines in the USA'
    description     TEXT,
    filter_config   JSONB NOT NULL,         -- {"vehicle_color":"red","vehicle_type_slugs":["stretch_limo"]}
    meta_title      TEXT,
    meta_description TEXT,
    is_active       BOOLEAN DEFAULT TRUE,
    created_at      TIMESTAMPTZ DEFAULT NOW()
);

-- ============================================================
-- SCRAPE LOGS
-- ============================================================
CREATE TABLE scrape_logs (
    id              SERIAL PRIMARY KEY,
    run_id          UUID DEFAULT uuid_generate_v4(),
    spider_name     TEXT NOT NULL,
    state           CHAR(2),
    status          TEXT DEFAULT 'running',  -- 'running' | 'done' | 'failed'
    companies_found INTEGER DEFAULT 0,
    companies_new   INTEGER DEFAULT 0,
    companies_updated INTEGER DEFAULT 0,
    errors          JSONB DEFAULT '[]',
    started_at      TIMESTAMPTZ DEFAULT NOW(),
    finished_at     TIMESTAMPTZ
);

-- ============================================================
-- UPDATED_AT trigger (auto-updates updated_at on companies)
-- ============================================================
CREATE OR REPLACE FUNCTION update_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trg_companies_updated_at
    BEFORE UPDATE ON companies
    FOR EACH ROW EXECUTE FUNCTION update_updated_at();

-- ============================================================
-- USEFUL VIEWS
-- ============================================================

-- Companies enriched with vehicle count and event tags
CREATE VIEW v_companies_enriched AS
SELECT
    c.*,
    COUNT(DISTINCT v.id)           AS vehicle_count,
    COUNT(DISTINCT vi.id)          AS image_count,
    ARRAY_AGG(DISTINCT v.primary_color) FILTER (WHERE v.primary_color IS NOT NULL) AS vehicle_colors,
    ARRAY_AGG(DISTINCT vt.slug)    FILTER (WHERE vt.slug IS NOT NULL)    AS vehicle_type_slugs,
    ARRAY_AGG(DISTINCT et.slug)    FILTER (WHERE et.slug IS NOT NULL)    AS event_type_slugs
FROM companies c
LEFT JOIN vehicles v         ON v.company_id = c.id
LEFT JOIN vehicle_types vt   ON vt.id = v.vehicle_type_id
LEFT JOIN vehicle_images vi  ON vi.company_id = c.id
LEFT JOIN company_event_tags cet ON cet.company_id = c.id
LEFT JOIN event_types et     ON et.id = cet.event_type_id
GROUP BY c.id;

-- Directory → matching companies (dynamic via filter_config)
-- Used by the API to resolve each directory slug
COMMENT ON TABLE directories IS
  'Each row defines a niche directory. The API reads filter_config to query v_companies_enriched.';