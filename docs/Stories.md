| Priority | Story | Acceptance Criteria | Notes |
|----------|-------|---------------------|-------|
| **Collector Epic** |
| P0 | Set up crawler infrastructure | **Given** a new source URL<br>**When** I configure it in the system<br>**Then** the crawler can fetch the page and store raw HTML | Base crawler with configurable politeness settings |
| P0 | Create source configuration model | **Given** I need to add a new source<br>**When** I define it in the system<br>**Then** I can specify URL, crawl frequency, parser type, and site association | Support for different parser types |
| P0 | Implement Music Farm venue crawler | **Given** the Music Farm calendar URL<br>**When** the crawler runs<br>**Then** it extracts all upcoming events with dates, times, and details | First production venue |
| P1 | Implement Pour House venue crawler | **Given** the Pour House calendar URL<br>**When** the crawler runs<br>**Then** it extracts all upcoming events with dates, times, and details | Second production venue |
| P1 | Implement Ticketmaster event crawler | **Given** Charleston Ticketmaster events<br>**When** the crawler runs<br>**Then** it extracts all music events in the Charleston metro area | API-based crawler |
| P2 | Implement Playwright fallback | **Given** a JavaScript-heavy source<br>**When** static crawling fails<br>**Then** the system falls back to Playwright for rendering | For complex sites only |
| **Normalizer Epic** |
| P0 | Create normalized event schema | **Given** raw event data<br>**When** stored in the database<br>**Then** it follows a consistent schema with required fields | Define DB schema first |
| P0 | Implement date/time normalizer | **Given** various date/time formats<br>**When** normalizing<br>**Then** produce consistent UTC timestamps with timezone info | Handle ambiguous times |
| P1 | Implement price normalizer | **Given** various price formats (free, $10, $10-15)<br>**When** normalizing<br>**Then** extract min/max price and currency | Handle "donation" and other edge cases |
| P1 | Implement age restriction normalizer | **Given** text with age information<br>**When** normalizing<br>**Then** extract standardized age restriction (all ages, 18+, 21+) | Default to unknown if not specified |
| **Deduper Epic** |
| P0 | Implement venue geocoding | **Given** a venue name and address<br>**When** geocoding<br>**Then** store lat/long coordinates with cache | Use Geoapify with caching |
| P1 | Implement exact-match deduplication | **Given** events from multiple sources<br>**When** they have identical key fields<br>**Then** merge them with source attribution | Define key fields for exact match |
| P2 | Implement fuzzy-match deduplication | **Given** similar events from different sources<br>**When** they likely refer to the same event<br>**Then** flag for review or auto-merge based on confidence | Title similarity + venue + date proximity |
| **API Epic** |
| P0 | Implement events read API | **Given** a request for events<br>**When** filtered by date range<br>**Then** return normalized events with pagination | Support filtering by venue, date range |
| P1 | Implement venue read API | **Given** a request for venues<br>**When** called<br>**Then** return all venues with details and geocodes | Support filtering by area |
| P1 | Implement source attribution API | **Given** a request for an event<br>**When** including attribution flag<br>**Then** include all source URLs for the event | For transparency |
| **Admin Epic** |
| P0 | Create ingest run dashboard | **Given** I'm an admin<br>**When** I view the dashboard<br>**Then** I see recent crawler runs with success/failure status | Show counts of new/updated events |
| P1 | Implement source health monitoring | **Given** a source has failed multiple times<br>**When** I view the dashboard<br>**Then** it's highlighted with error details | Track error patterns |
| P2 | Create manual override interface | **Given** incorrect event data<br>**When** I edit it in the admin interface<br>**Then** it's corrected without affecting future crawls | For emergency fixes |
| **Ops Epic** |
| P0 | Set up database migrations | **Given** schema changes<br>**When** deploying<br>**Then** Flyway applies migrations correctly | DB-first approach |
| P0 | Implement structured logging | **Given** system operations<br>**When** actions occur<br>**Then** JSON logs are generated with context | For observability |
| P1 | Create E2E test fixtures | **Given** the need to test crawlers<br>**When** running tests<br>**Then** use golden fixtures instead of live requests | For deterministic CI |
| P1 | Implement R2 artifact storage | **Given** raw HTML/JSON from crawls<br>**When** stored<br>**Then** save to R2 with 30-day lifecycle | For debugging and replay |
