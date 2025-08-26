# MusicLive: Multi-site Live Music Event Collector and API

## Problem Statement
Music fans in Charleston struggle to discover live music events across multiple venues and platforms. Venues publish events in inconsistent formats across websites, social media, and ticketing platforms, making comprehensive discovery difficult.

## Users
- **Music Fans**: Access comprehensive event data through future API consumers
- **Site Administrators**: Monitor crawler health, fix source issues quickly

## Success Metrics
1. **Coverage**: 95% of live music events in Charleston metro captured
2. **Freshness**: 90% of events updated within 24 hours of source changes
3. **Accuracy**: <2% error rate in normalized event data
4. **Efficiency**: Average crawl cost <$0.05 per source per day

## In-Scope
- Crawl configured venue calendars, ticketing pages, and event feeds in Charleston metro
- Extract and normalize event data (title, time, venue, price, age restrictions, URL)
- Geocode venues with caching
- Deduplicate events across sources
- Read-only API for consumers
- Internal admin dashboard for monitoring

## Out-of-Scope
- Public-facing website
- User authentication/authorization
- Notifications or alerts
- Payment processing
- Machine learning recommendations
- General web crawling
- Events outside Charleston metro
- Recurring event rule (RRULE) processing

## Non-Functional Requirements
1. **Cost Efficiency**
   - Minimize API/headless browser usage
   - Store raw artifacts in R2 with 30-day retention
   - Ability to inspect raw artifacts and correct event/venue data inline.
   - Preserve source attribution when deduping; conflicts flagged for admin, not silently discarded.

2. **Crawler Politeness**
   - Honor robots.txt directives
   - No login/paywall circumvention
   - Per-source rate limits with jitter

3. **Reliability**
   - Cron-based scheduling initially
   - Design for future Redis/RQ implementation

4. **Observability**
   - JSON structured logging
   - Ingest run tracking table
   - Simple performance counters
   - Dev/test environment parity

5. **Testing**
   - Golden fixture E2E tests
   - Recorded fixtures for CI (no live hits)
   - Unit tests for extractors/normalizer

## Risks & Mitigations

| Risk | Impact | Likelihood | Mitigation |
|------|--------|------------|------------|
| Source format changes | High | Medium | Modular extractors, monitoring, alerts on failure |
| Rate limiting/blocking | High | Medium | Per-source politeness settings, Playwright fallback |
| Duplicate events | Medium | High | Multi-strategy deduplication, source attribution |
| Geocoding failures | Low | Low | Caching, fallback coordinates, manual override |
| Database costs | Medium | Low | Efficient schema, indexes, query optimization |

## Rollout Plan
1. **Phase 1**: Initial crawlers for 5 major Charleston venues (2 weeks)
2. **Phase 2**: Normalization, deduplication, and API (2 weeks)
3. **Phase 3**: Admin dashboard and monitoring (1 week)
4. **Phase 4**: Expand to remaining Charleston metro venues (3 weeks)
5. **Phase 5**: Optimization and stabilization (2 weeks)
