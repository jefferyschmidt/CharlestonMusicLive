import os
import uuid
from datetime import datetime, timezone

import pytest

from db.persistence import get_connection, ensure_site, ensure_source, upsert_venue, insert_event_instance, upsert_event_source_link


@pytest.mark.skipif(not os.getenv("DATABASE_URL"), reason="DATABASE_URL not set")
def test_upserts_end_to_end():
    slug = f"testsite_{uuid.uuid4().hex[:8]}"
    with get_connection() as conn:
        conn.execute("BEGIN")
        try:
            # Ensure site and source
            site_id = ensure_site(conn, slug, display_name=f"Test {slug}")
            source_id = ensure_source(conn, site_id, name="Sample Source", url="https://example.com/sample")

            # Upsert venue
            venue_id = upsert_venue(conn, site_id, name="Test Venue", city="Charleston", state="SC")

            # Insert event instance
            starts = datetime(2030, 1, 1, 1, 0, 0, tzinfo=timezone.utc)
            event_id = insert_event_instance(
                conn,
                site_id,
                venue_id,
                title="Test Event",
                description="Desc",
                artist_name="Artist",
                starts_at_utc=starts,
                ends_at_utc=None,
                tz_name="America/New_York",
                doors_time_utc=None,
                price_min=10.0,
                price_max=20.0,
                currency="USD",
                ticket_url="https://tickets.example.com/x",
                age_restriction="21+",
                is_cancelled=False,
                source_created_at=None,
                source_updated_at=None,
            )

            # Upsert event source link
            link_id = upsert_event_source_link(
                conn,
                event_instance_id=event_id,
                source_id=source_id,
                ingest_run_id=None,
                external_id="abc123",
                source_url="https://example.com/sample/event",
                raw_data={"check": True},
            )

            assert site_id and source_id and venue_id and event_id and link_id
        finally:
            conn.execute("ROLLBACK")
