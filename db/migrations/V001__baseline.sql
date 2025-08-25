CREATE TABLE IF NOT EXISTS site (
  id BIGSERIAL PRIMARY KEY,
  site_slug TEXT NOT NULL UNIQUE,
  display_name TEXT NOT NULL,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS source (
  id BIGSERIAL PRIMARY KEY,
  site_id BIGINT NOT NULL REFERENCES site(id) ON DELETE CASCADE,
  name TEXT NOT NULL,
  url TEXT NOT NULL,
  requires_browser BOOLEAN NOT NULL DEFAULT FALSE,
  rate_limit_rps NUMERIC(6,3) NOT NULL DEFAULT 1.000,
  active BOOLEAN NOT NULL DEFAULT TRUE,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS ingest_run (
  id BIGSERIAL PRIMARY KEY,
  source_id BIGINT NOT NULL REFERENCES source(id) ON DELETE CASCADE,
  started_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  finished_at TIMESTAMPTZ,
  status TEXT NOT NULL DEFAULT 'running',
  error TEXT
);

CREATE INDEX IF NOT EXISTS idx_source_site ON source(site_id);
CREATE INDEX IF NOT EXISTS idx_ingest_run_source_started ON ingest_run(source_id, started_at DESC);
