# orchestrator/run_db_modeler.py
import os
import pathlib
from anthropic import Anthropic

ROOT = pathlib.Path(__file__).resolve().parents[1]
DOCS = ROOT / "docs"
DB_MIGR = ROOT / "db" / "migrations"
DB_MIGR.mkdir(parents=True, exist_ok=True)

SYSTEM_RULES = """You are a senior PostgreSQL schema designer working DB-first with Flyway.
You MUST:
- Inspect the provided V001__baseline.sql and treat it as SOURCE OF TRUTH.
- DO NOT recreate or rename existing tables/columns from V001 (site, source, ingest_run).
- Extend existing tables only via: ALTER TABLE ... ADD COLUMN IF NOT EXISTS / CREATE INDEX IF NOT EXISTS.
- Create NEW tables with CREATE TABLE IF NOT EXISTS.
- Use agreed time fields for events: starts_at_utc, ends_at_utc, tz_name.
- No artist table in MVP; store artist_name inline on event rows.
- Use sensible FKs with ON DELETE CASCADE where appropriate (venue/events), SET NULL for optional linkages.
- Add useful indexes (site_id, time, FKs).
- Keep it idempotent and executable by Flyway (no psql meta-commands).
- OUTPUT ONLY raw SQL. NO explanations, NO code fences.
"""

USER_PROMPT = """Goal: Produce V002__core_entities.sql that builds on V001.

Context (summaries):
- PRD/Stories/Glossary describe a Charleston-only MVP, configured sources only, dedup with source attribution, raw artifacts to R2, geocoding cache, admin dashboard. No public frontend.
- Core entities to add: venue, event_instance, event_source_link (attribution), raw_artifact, geocode_cache.
- Extend source with optional crawl/politeness knobs (parser_type, politeness_delay_ms, respect_robots_txt, updated_at) without breaking V001.

Requirements:
- DO NOT touch or recreate tables from V001: site(id, site_slug, display_name, created_at), source(id, site_id, name, url, requires_browser, rate_limit_rps, active, created_at), ingest_run(id, source_id, started_at, finished_at, status, error).
- Create NEW tables:
  * venue(site_id FK, unique (site_id, name), optional address fields, latitude/longitude, tz_name).
  * event_instance(site_id, venue_id, title, description, artist_name, starts_at_utc, ends_at_utc, tz_name, doors_time_utc, price_min/max, currency, ticket_url, age_restriction, is_cancelled, source_created_at, source_updated_at, created_at, updated_at).
  * event_source_link(event_instance_id, source_id, ingest_run_id, external_id, source_url, raw_data JSONB, created_at/updated_at) with UNIQUE(event_instance_id, source_id).
  * raw_artifact(ingest_run_id, storage_key UNIQUE, content_type, size_bytes, etag, created_at).
  * geocode_cache(address_hash UNIQUE, address, latitude, longitude, raw_response JSONB, created_at, expires_at).
- Extend existing table:
  * ALTER TABLE source ADD COLUMN IF NOT EXISTS parser_type TEXT;
  * ALTER TABLE source ADD COLUMN IF NOT EXISTS politeness_delay_ms INTEGER DEFAULT 1000;
  * ALTER TABLE source ADD COLUMN IF NOT EXISTS respect_robots_txt BOOLEAN DEFAULT TRUE;
  * ALTER TABLE source ADD COLUMN IF NOT EXISTS updated_at TIMESTAMPTZ DEFAULT now();
  * CREATE INDEX IF NOT EXISTS on source(active) if not present.
- Add reasonable indexes: by site_id, venue_id, starts_at_utc, booleans, FKs.
- Keep comments concise with COMMENT ON TABLE/COLUMN where useful.

Deliverable:
Return ONLY the full SQL migration body for V002__core_entities.sql. No prose.
"""

def _read(path: pathlib.Path) -> str:
    return path.read_text(encoding="utf-8") if path.exists() else ""

def main() -> None:
    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        raise SystemExit("ANTHROPIC_API_KEY not set")

    client = Anthropic(api_key=api_key)
    model = os.environ.get("ANTHROPIC_MODEL", "claude-3-7-sonnet-latest")

    # Load docs and baseline
    prd = _read(DOCS / "PRD.md")
    stories = _read(DOCS / "Stories.md")
    glossary = _read(DOCS / "Glossary.md")
    baseline = _read(DB_MIGR / "V001__baseline.sql")
    if not baseline:
        raise SystemExit("V001__baseline.sql not found in db/migrations; required for modeling.")

    resp = client.messages.create(
        model=model,
        max_tokens=3500,
        temperature=0.1,
        system=SYSTEM_RULES,
        messages=[{
            "role": "user",
            "content": [
                {"type": "text", "text": USER_PROMPT},
                {"type": "text", "text": "===V001_BASELINE_SQL===\n" + baseline},
                {"type": "text", "text": "===PRD===\n" + prd},
                {"type": "text", "text": "===STORIES===\n" + stories},
                {"type": "text", "text": "===GLOSSARY===\n" + glossary},
            ],
        }],
    )

    # Extract raw text (SQL only per instructions)
    sql_parts = []
    for block in resp.content or []:
        if getattr(block, "type", "") == "text":
            sql_parts.append(block.text)
    sql = "".join(sql_parts).strip()

    # Strip accidental code fences if any
    if sql.startswith("```"):
        sql = sql.strip("` \n")
        # remove leading language tag if present
        if sql.startswith("sql"):
            sql = sql[3:].lstrip()

    out = DB_MIGR / "V002__core_entities.sql"
    out.write_text(sql + "\n", encoding="utf-8")
    print("Wrote:", out)

if __name__ == "__main__":
    main()
