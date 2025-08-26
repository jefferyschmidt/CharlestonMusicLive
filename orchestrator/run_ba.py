# orchestrator/run_ba.py
import os
import pathlib
from anthropic import Anthropic

ROOT = pathlib.Path(__file__).resolve().parents[1]
DOCS = ROOT / "docs"
DOCS.mkdir(parents=True, exist_ok=True)

BASE_CONTEXT = """Project: MusicLive — multi-site live-music event collector and read API.

Primary site to start:
- CharlestonMusicLive.com  (site_slug = "charleston")

Geography (MVP):
- Only crawl sources in the Charleston metro region (Charleston, North Charleston, Mount Pleasant, Summerville, Ladson, Goose Creek, Moncks Corner, Isle of Palms, Folly Beach, James Island, Johns Island, Daniel Island).
- Out-of-scope: events outside the Charleston metro.

Discovery scope:
- ✅ IMPLEMENTED: Intelligent self-discovering crawler that automatically finds venue calendars and event sources
- ✅ IMPLEMENTED: Multi-strategy discovery (search engines, aggregators, cross-referencing, business directories)
- ✅ IMPLEMENTED: Automatic source analysis and venue type classification
- ✅ IMPLEMENTED: Adaptive extractor selection and generation
- ✅ IMPLEMENTED: No more manual venue list configuration needed

Target users:
- Music fans (via future API consumers; no public frontend in this MVP).
- Site admin (internal): observe crawler health, fix sources quickly.

Scope (IN):
- ✅ IMPLEMENTED: Crawl multiple sources per site with intelligent discovery
- ✅ IMPLEMENTED: Extract concrete event instances (no RRULEs)
- ✅ IMPLEMENTED: Normalize (title, starts_at_utc, ends_at_utc, tz_name, venue, price, age, url)
- ✅ IMPLEMENTED: Database persistence with upsert functions
- ✅ IMPLEMENTED: Read-only API with advanced filtering and search
- ✅ IMPLEMENTED: Raw artifact storage (R2/S3 compatible)
- ✅ IMPLEMENTED: CLI tools for parsing, ingestion, and discovery
- ✅ IMPLEMENTED: Sample venue extractor (SampleVenueExtractor)
- ✅ IMPLEMENTED: Real venue extractor (MusicFarmExtractor)
- ✅ IMPLEMENTED: Extractor factory for adaptive selection
- ✅ IMPLEMENTED: Source discovery engine with confidence scoring
- ✅ IMPLEMENTED: Intelligent crawler with learning capabilities
- ✅ IMPLEMENTED: Database schema with site, source, venue, event_instance tables
- ✅ IMPLEMENTED: FastAPI endpoints for events, venues, search, and admin
- ✅ IMPLEMENTED: Deployment configuration (Fly.io, Docker, GitHub Actions)
- ✅ IMPLEMENTED: Comprehensive testing framework with fixtures
- ✅ IMPLEMENTED: BMAD agent system for automated development pipeline

Scope (OUT):
- No public-facing website, SEO, auth, notifications, payments, ML/recommendations.

Non-functional:
- ✅ IMPLEMENTED: Cost: minimize API/headless usage; raw artifacts stored to R2 with 30-day lifecycle
- ✅ IMPLEMENTED: Politeness/legal: honor robots.txt by default; no login/paywall scraping; per-source rate limits + jitter
- ✅ IMPLEMENTED: Reliability: cron-only now; keep seams for Redis/RQ later
- ✅ IMPLEMENTED: Observability: JSON logs, ingest_run table, simple counters; dev/test parity
- ✅ IMPLEMENTED: CI determinism: tests use recorded fixtures only (no live hits in CI)

Architecture (fixed):
- ✅ IMPLEMENTED: Python 3.11 + FastAPI; httpx + selectolax; Playwright fallback
- ✅ IMPLEMENTED: Postgres (Neon); Flyway SQL migrations (DB-first)
- ✅ IMPLEMENTED: Time: store starts_at_utc, ends_at_utc, tz_name
- ✅ IMPLEMENTED: Tenancy: single DB; tables carry site_id
- ✅ IMPLEMENTED: Geocoding: Geoapify (cached)

NEW REQUIREMENTS DISCOVERED DURING DEVELOPMENT:

1. **Intelligent Discovery System**:
   - Self-discovering crawler that finds venues automatically
   - Multi-strategy source discovery (search engines, aggregators, cross-referencing)
   - Automatic venue type classification (concert venue, bar, restaurant, outdoor)
   - Calendar detection and event content analysis
   - Confidence scoring for source quality
   - Learning and adaptation from successful/failed extractions

2. **Adaptive Extractor System**:
   - Extractor factory for intelligent selection
   - Generic AdaptiveExtractor for unknown venue types
   - Pattern learning and improvement over time
   - Fallback strategies for various venue structures

3. **Enhanced API Capabilities**:
   - Advanced filtering (artist search, price range, age restrictions)
   - Unified search across events and venues
   - Detailed venue and event information endpoints
   - Pagination and result optimization

4. **Storage and Persistence**:
   - R2/S3 compatible storage for raw artifacts
   - Database upsert functions for atomic operations
   - Transaction management for ingestion operations
   - Source attribution and ingest run tracking

5. **Deployment and Operations**:
   - Fly.io deployment with Docker
   - GitHub Actions CI/CD pipeline
   - Database migration automation
   - Health checks and monitoring

6. **CLI and Tooling**:
   - Parse, ingest, and discover commands
   - Dynamic extractor selection
   - Batch processing capabilities
   - Error handling and reporting

CURRENT STATE:
- All core BMAD agents are built and functional
- Intelligent discovery system is implemented and tested
- Database persistence layer is complete
- API endpoints are functional with advanced features
- Deployment infrastructure is configured
- Comprehensive testing framework is in place
- The system is ready for production use and scaling to other cities

NEXT PHASE REQUIREMENTS:
- Production deployment and monitoring
- Scaling to additional cities (Nashville, Memphis, New Orleans)
- Enhanced admin dashboard functionality
- Real-time event monitoring and updates
- Performance optimization and scaling
- Additional venue extractors for discovered sources
"""

INSTRUCTIONS = """Using the context and stakeholder answers, produce three sections with HARD MARKERS.

You MUST output in this exact order with these literal markers on their own lines:
===PRD===
...content...
===STORIES===
...table...
===GLOSSARY===
...content...

Details:

PRD:
- Problem, users, success metrics (numeric targets).
- In-scope / out-of-scope.
- Non-functional requirements.
- Risks & mitigations.
- Rollout plan.

STORIES:
- Backlog table: | Priority | Story | Acceptance Criteria (Given/When/Then) | Notes |
- 15–25 stories grouped by epic (Collector, Normalizer, Deduper, API, Admin, Ops).
- Acceptance criteria MUST be concrete/testable.

GLOSSARY:
- Define: site, source, venue, event instance, ingest run, raw artifact, normalizer, deduper, geocode cache.

Style:
- Concise, implementable; prefer lists/tables.
- ≤1500 words total.
"""

def _anthropic_client():
    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        raise SystemExit("ANTHROPIC_API_KEY not set")
    return Anthropic(api_key=api_key), os.environ.get("ANTHROPIC_MODEL", "claude-3-7-sonnet-latest")

def _extract_text(resp):
    blocks = []
    for b in resp.content or []:
        if getattr(b, "type", "") == "text":
            blocks.append(b.text)
    return "\n".join(blocks).strip()

def _parse_by_markers(text: str):
    prd = stories = glossary = ""
    cur = None
    out = {"PRD": [], "STORIES": [], "GLOSSARY": []}
    for line in text.splitlines():
        if line.strip() == "===PRD===":
            cur = "PRD";  # start PRD
            continue
        if line.strip() == "===STORIES===":
            cur = "STORIES";  # start STORIES
            continue
        if line.strip() == "===GLOSSARY===":
            cur = "GLOSSARY";  # start GLOSSARY
            continue
        if cur:
            out[cur].append(line)
    return ("\n".join(out["PRD"]).strip(),
            "\n".join(out["STORIES"]).strip(),
            "\n".join(out["GLOSSARY"]).strip())

def main():
    client, model = _anthropic_client()
    answers = (DOCS / "BA_Answers.md").read_text(encoding="utf-8") if (DOCS / "BA_Answers.md").exists() else "(No BA_Answers.md found; proceed using context only.)"

    # Single call for all three docs
    resp = client.messages.create(
        model=model,
        max_tokens=2500,
        temperature=0.2,
        messages=[{
            "role": "user",
            "content": [
                {"type": "text", "text": BASE_CONTEXT},
                {"type": "text", "text": "Stakeholder Answers:\n" + answers},
                {"type": "text", "text": INSTRUCTIONS},
            ],
        }],
    )
    all_text = _extract_text(resp)

    prd, stories, glossary = _parse_by_markers(all_text)

    # If PRD came back empty, ask for PRD only as a fallback (keeps momentum)
    if not prd.strip():
        prd_only = client.messages.create(
            model=model,
            max_tokens=1200,
            temperature=0.2,
            messages=[{
                "role": "user",
                "content": [
                    {"type": "text", "text": BASE_CONTEXT},
                    {"type": "text", "text": "Stakeholder Answers:\n" + answers},
                    {"type": "text", "text": "Write the PRD only, concise and implementable. Sections: Problem; Users; Success Metrics (numerical targets); In-scope; Out-of-scope; Non-functional; Risks & mitigations; Rollout plan. Avoid fluff."},
                ],
            }],
        )
        prd = _extract_text(prd_only)

    # Write files (don’t overwrite a non-empty Stories.md if you already like it)
    (DOCS / "PRD.md").write_text(prd.strip() + "\n", encoding="utf-8")
    if stories:
        (DOCS / "Stories.md").write_text(stories.strip() + "\n", encoding="utf-8")
    if glossary:
        (DOCS / "Glossary.md").write_text(glossary.strip() + "\n", encoding="utf-8")

    wrote = []
    for name in ("PRD.md", "Stories.md", "Glossary.md"):
        p = DOCS / name
        if p.exists() and p.stat().st_size > 0:
            wrote.append(name)
    print("Wrote:", wrote)

if __name__ == "__main__":
    main()
