- **Site**: A geographic music scene with its own domain (e.g., CharlestonMusicLive.com). Identified by a unique slug (e.g., "charleston").

- **Source**: A specific URL or API endpoint that provides event information (e.g., a venue's calendar page, ticketing site). Each source has configuration for crawl frequency, parser type, and politeness settings.

- **Venue**: A physical location where music events occur. Includes name, address, and geocoded coordinates.

- **Event Instance**: A specific occurrence of a music event with concrete date/time. Contains normalized data including title, start/end times, venue, price, age restrictions, and source URL.

- **Ingest Run**: A single execution of the crawler against a specific source, tracked with metadata about success/failure, timing, and event counts.

- **Raw Artifact**: The unprocessed HTML, JSON, or other data captured from a source during an ingest run. Stored in R2 for debugging and replay.

- **Normalizer**: Component that transforms raw event data from various formats into a standardized schema with consistent field formats.

- **Deduper**: System that identifies and merges duplicate events from different sources, preserving attribution to all original sources.

- **Geocode Cache**: Database of venue locations with their corresponding latitude/longitude coordinates, reducing redundant geocoding API calls.
