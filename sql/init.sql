CREATE TABLE IF NOT EXISTS du_chapters (
    chapter_id   TEXT        PRIMARY KEY,
    chapter_name TEXT        NOT NULL,
    city         TEXT,
    state        TEXT        NOT NULL,
    coordinates  JSONB,
    loaded_at    TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_du_chapters_state ON du_chapters (state);

COMMENT ON TABLE du_chapters IS
    'Ducks Unlimited university chapters sourced from the DU ArcGIS FeatureServer API.';
COMMENT ON COLUMN du_chapters.coordinates IS
    'GeoJSON-style point as JSONB: {"latitude": float, "longitude": float}';
COMMENT ON COLUMN du_chapters.loaded_at IS
    'Timestamp of the most recent upsert for this row.';
