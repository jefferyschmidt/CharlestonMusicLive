-- V002__core_entities.sql

-- Extend source table with new columns
ALTER TABLE source ADD COLUMN IF NOT EXISTS parser_type TEXT;
ALTER TABLE source ADD COLUMN IF NOT EXISTS politeness_delay_ms INTEGER DEFAULT 1000;
ALTER TABLE source ADD COLUMN IF NOT EXISTS respect_robots_txt BOOLEAN DEFAULT TRUE;
ALTER TABLE source ADD COLUMN IF NOT EXISTS updated_at TIMESTAMPTZ DEFAULT now();
CREATE INDEX IF NOT EXISTS idx_source_active ON source(active);

-- Create venue table
CREATE TABLE IF NOT EXISTS venue (
  id BIGSERIAL PRIMARY KEY,
  site_id BIGINT NOT NULL REFERENCES site(id) ON DELETE CASCADE,
  name TEXT NOT NULL,
  address_line1 TEXT,
  address_line2 TEXT,
  city TEXT,
  state TEXT,
  postal_code TEXT,
  country TEXT DEFAULT 'US',
  latitude DECIMAL(10, 7),
  longitude DECIMAL(10, 7),
  tz_name TEXT DEFAULT 'America/New_York',
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  UNIQUE(site_id, name)
);
COMMENT ON TABLE venue IS 'Physical locations where events take place';
COMMENT ON COLUMN venue.tz_name IS 'IANA timezone identifier for the venue location';

CREATE INDEX IF NOT EXISTS idx_venue_site ON venue(site_id);
CREATE INDEX IF NOT EXISTS idx_venue_location ON venue(latitude, longitude) WHERE latitude IS NOT NULL AND longitude IS NOT NULL;

-- Create event_instance table
CREATE TABLE IF NOT EXISTS event_instance (
  id BIGSERIAL PRIMARY KEY,
  site_id BIGINT NOT NULL REFERENCES site(id) ON DELETE CASCADE,
  venue_id BIGINT REFERENCES venue(id) ON DELETE SET NULL,
  title TEXT NOT NULL,
  description TEXT,
  artist_name TEXT,
  starts_at_utc TIMESTAMPTZ NOT NULL,
  ends_at_utc TIMESTAMPTZ,
  tz_name TEXT NOT NULL DEFAULT 'America/New_York',
  doors_time_utc TIMESTAMPTZ,
  price_min DECIMAL(10, 2),
  price_max DECIMAL(10, 2),
  currency TEXT DEFAULT 'USD',
  ticket_url TEXT,
  age_restriction TEXT,
  is_cancelled BOOLEAN DEFAULT FALSE,
  source_created_at TIMESTAMPTZ,
  source_updated_at TIMESTAMPTZ,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
COMMENT ON TABLE event_instance IS 'Normalized music events with venue and time information';
COMMENT ON COLUMN event_instance.tz_name IS 'IANA timezone identifier for event times';

CREATE INDEX IF NOT EXISTS idx_event_instance_site ON event_instance(site_id);
CREATE INDEX IF NOT EXISTS idx_event_instance_venue ON event_instance(venue_id);
CREATE INDEX IF NOT EXISTS idx_event_instance_starts_at ON event_instance(starts_at_utc);
CREATE INDEX IF NOT EXISTS idx_event_instance_cancelled ON event_instance(is_cancelled) WHERE is_cancelled = TRUE;
CREATE INDEX IF NOT EXISTS idx_event_instance_artist ON event_instance(artist_name) WHERE artist_name IS NOT NULL;

-- Create event_source_link table for attribution
CREATE TABLE IF NOT EXISTS event_source_link (
  id BIGSERIAL PRIMARY KEY,
  event_instance_id BIGINT NOT NULL REFERENCES event_instance(id) ON DELETE CASCADE,
  source_id BIGINT NOT NULL REFERENCES source(id) ON DELETE CASCADE,
  ingest_run_id BIGINT REFERENCES ingest_run(id) ON DELETE SET NULL,
  external_id TEXT,
  source_url TEXT NOT NULL,
  raw_data JSONB,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  UNIQUE(event_instance_id, source_id)
);
COMMENT ON TABLE event_source_link IS 'Links events to their original sources for attribution and deduplication';
COMMENT ON COLUMN event_source_link.external_id IS 'ID of the event in the source system';
COMMENT ON COLUMN event_source_link.raw_data IS 'Normalized but source-specific data for this event';

CREATE INDEX IF NOT EXISTS idx_event_source_link_event ON event_source_link(event_instance_id);
CREATE INDEX IF NOT EXISTS idx_event_source_link_source ON event_source_link(source_id);
CREATE INDEX IF NOT EXISTS idx_event_source_link_ingest ON event_source_link(ingest_run_id);
CREATE INDEX IF NOT EXISTS idx_event_source_link_external_id ON event_source_link(external_id) WHERE external_id IS NOT NULL;

-- Create raw_artifact table for storing references to R2 objects
CREATE TABLE IF NOT EXISTS raw_artifact (
  id BIGSERIAL PRIMARY KEY,
  ingest_run_id BIGINT NOT NULL REFERENCES ingest_run(id) ON DELETE CASCADE,
  storage_key TEXT NOT NULL UNIQUE,
  content_type TEXT NOT NULL,
  size_bytes INTEGER NOT NULL,
  etag TEXT,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
COMMENT ON TABLE raw_artifact IS 'References to raw HTML/JSON artifacts stored in R2';
COMMENT ON COLUMN raw_artifact.storage_key IS 'R2 object key for the stored artifact';
COMMENT ON COLUMN raw_artifact.etag IS 'ETag from R2 for content validation';

CREATE INDEX IF NOT EXISTS idx_raw_artifact_ingest ON raw_artifact(ingest_run_id);

-- Create geocode_cache table
CREATE TABLE IF NOT EXISTS geocode_cache (
  id BIGSERIAL PRIMARY KEY,
  address_hash TEXT NOT NULL UNIQUE,
  address TEXT NOT NULL,
  latitude DECIMAL(10, 7) NOT NULL,
  longitude DECIMAL(10, 7) NOT NULL,
  raw_response JSONB,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  expires_at TIMESTAMPTZ NOT NULL
);
COMMENT ON TABLE geocode_cache IS 'Cached geocoding results to minimize API calls';
COMMENT ON COLUMN geocode_cache.address_hash IS 'Hash of the normalized address string';
COMMENT ON COLUMN geocode_cache.raw_response IS 'Complete response from geocoding provider';
COMMENT ON COLUMN geocode_cache.expires_at IS 'When this cache entry should be refreshed';

CREATE INDEX IF NOT EXISTS idx_geocode_cache_expires ON geocode_cache(expires_at);

-- Add trigger to update timestamps
CREATE OR REPLACE FUNCTION update_timestamp()
RETURNS TRIGGER AS $$
BEGIN
  NEW.updated_at = now();
  RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER update_source_timestamp
BEFORE UPDATE ON source
FOR EACH ROW EXECUTE FUNCTION update_timestamp();

CREATE TRIGGER update_venue_timestamp
BEFORE UPDATE ON venue
FOR EACH ROW EXECUTE FUNCTION update_timestamp();

CREATE TRIGGER update_event_instance_timestamp
BEFORE UPDATE ON event_instance
FOR EACH ROW EXECUTE FUNCTION update_timestamp();

CREATE TRIGGER update_event_source_link_timestamp
BEFORE UPDATE ON event_source_link
FOR EACH ROW EXECUTE FUNCTION update_timestamp();
