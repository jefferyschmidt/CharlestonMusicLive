1. What specific data fields need to be collected for each artist (e.g., name, genre, social media links, upcoming events, etc.)?
At MVP, we’re not tracking artists directly. Collect only what comes naturally with an event: artist name (as text string in lineup), optional genre (if provided by source), and link to artist page (if source gives it).

No dedicated artist entity for now; just store names/lineups as part of the event. Future versions may add richer artist modeling.

2. What are the rate limits for each API we'll be accessing (Spotify, Ticketmaster, etc.), and how should we handle them?
Rate limits vary by source; collector should default to a configurable per-source rate limit (e.g., 1 request/sec).

Keep crawler polite (respect robots.txt, jitter requests).

Do not assume unlimited access.


3. Are there geographic limitations for the concert data we should collect, or should we gather global event information?
Definitely limit the geography. For this stage, you should limit to the Charleston, South Carolina metro region including places like Mount Pleasant, Isle of Palms, Folly Beach, James Island, Johns Island, Daniel Island, Summerville, Ladson, Goose Creek, Monks Corner, etc.

Explicitly out-of-scope: events outside Charleston metro. If a source lists events in multiple cities, only ingest the Charleston ones.

4. What is the expected volume of artists to track, and how frequently should we update the data?
Remember that we're tracking live events (based mostly on venue), not tracking individual artists.

Volume unknown; design for dozens of venues, hundreds of events/month.

Frequency: cron-controlled; default daily, configurable by site.

5. What admin features are needed to manage the collector (e.g., adding/removing artists, viewing collection status, error reporting)?
Admin MVP: list of sources, last run status, errors.

Optional: inline edit/correct event/venue data.

No auth/user management yet.

6. What are the success metrics for this collector (e.g., data freshness, completeness, accuracy)?
Accuracy: ≥95% event details correct (time/date/venue).

Freshness: new/changed events appear within 24h of source update (when cron runs daily).

Completeness: ≥90% of events from configured sources are captured.

7. Are there any legal constraints or terms of service considerations when scraping data from artist websites or social media?
Only scrape publicly available pages; respect robots.txt unless explicitly overridden. No scraping behind login or paywalls.

8. How should we handle conflicting information from different sources (e.g., if Spotify and the artist's website list different tour dates)?
Store both versions with source attribution (so admin can resolve).

Deduper may flag conflicts, but don’t discard automatically.