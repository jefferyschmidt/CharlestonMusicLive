from fastapi import FastAPI, Query, HTTPException
from fastapi.responses import HTMLResponse
from typing import List, Optional
from datetime import datetime, date
import psycopg
import os
from dataclasses import dataclass

app = FastAPI(title="MusicLive Collector API")

# Data models for API responses
@dataclass
class VenueResponse:
    id: int
    name: str
    city: Optional[str]
    state: Optional[str]
    latitude: Optional[float]
    longitude: Optional[float]

@dataclass
class VenueDetailResponse:
    id: int
    name: str
    address_line1: Optional[str]
    city: Optional[str]
    state: Optional[str]
    postal_code: Optional[str]
    latitude: Optional[float]
    longitude: Optional[float]
    tz_name: str
    total_events: int

@dataclass
class EventResponse:
    id: int
    title: str
    artist_name: Optional[str]
    starts_at_utc: str
    ends_at_utc: Optional[str]
    venue_name: str
    price_min: Optional[float]
    price_max: Optional[float]
    currency: str
    ticket_url: Optional[str]
    age_restriction: Optional[str]

@dataclass
class EventDetailResponse:
    id: int
    title: str
    artist_name: Optional[str]
    starts_at_utc: str
    ends_at_utc: Optional[str]
    venue_name: str
    venue_id: Optional[int]
    price_min: Optional[float]
    price_max: Optional[float]
    currency: str
    ticket_url: Optional[str]
    age_restriction: Optional[str]
    is_cancelled: bool
    sources: List[dict]  # List of source attribution info

@dataclass
class SearchResponse:
    events: List[EventResponse]
    venues: List[VenueResponse]
    total_events: int
    total_venues: int
    query: str

@dataclass
class AdminStatusResponse:
    status: str
    timestamp: str
    database_connected: bool
    total_sites: Optional[int]
    total_sources: Optional[int]
    total_venues: Optional[int]
    total_events: Optional[int]

def get_db_connection():
    """Get database connection from environment."""
    database_url = os.getenv("DATABASE_URL")
    if not database_url:
        raise HTTPException(status_code=500, detail="Database not configured")
    return psycopg.connect(database_url)

@app.get("/", response_class=HTMLResponse)
def root():
    return "<h1>MusicLive Collector API</h1><p>Status: OK</p>"

@app.get("/admin/status", response_model=AdminStatusResponse)
def admin_status():
    """Admin endpoint to check system status and basic metrics."""
    try:
        with get_db_connection() as conn:
            with conn.cursor() as cur:
                # Get basic counts
                cur.execute("SELECT COUNT(*) FROM site")
                total_sites = cur.fetchone()[0]
                
                cur.execute("SELECT COUNT(*) FROM source")
                total_sources = cur.fetchone()[0]
                
                cur.execute("SELECT COUNT(*) FROM venue")
                total_venues = cur.fetchone()[0]
                
                cur.execute("SELECT COUNT(*) FROM event_instance")
                total_events = cur.fetchone()[0]
                
                return AdminStatusResponse(
                    status="healthy",
                    timestamp=datetime.utcnow().isoformat() + "Z",
                    database_connected=True,
                    total_sites=total_sites,
                    total_sources=total_sources,
                    total_venues=total_venues,
                    total_events=total_events
                )
    except Exception as e:
        return AdminStatusResponse(
            status="error",
            timestamp=datetime.utcnow().isoformat() + "Z",
            database_connected=False,
            total_sites=None,
            total_sources=None,
            total_venues=None,
            total_events=None
        )

@app.get("/api/v1/sites/{site_slug}/venues", response_model=List[VenueResponse])
def list_venues(
    site_slug: str,
    search: Optional[str] = Query(None, description="Search venues by name"),
    limit: int = Query(50, ge=1, le=100, description="Maximum number of venues to return"),
    offset: int = Query(0, ge=0, description="Number of venues to skip")
):
    """List venues for a specific site with optional search and pagination."""
    try:
        with get_db_connection() as conn:
            with conn.cursor() as cur:
                # First get the site_id
                cur.execute("SELECT id FROM site WHERE site_slug = %s", (site_slug,))
                site_result = cur.fetchone()
                if not site_result:
                    raise HTTPException(status_code=404, detail=f"Site '{site_slug}' not found")
                
                site_id = site_result[0]
                
                # Build the query with optional search
                query = """
                    SELECT id, name, city, state, latitude, longitude
                    FROM venue 
                    WHERE site_id = %s
                """
                params = [site_id]
                
                if search:
                    query += " AND name ILIKE %s"
                    params.append(f"%{search}%")
                
                query += " ORDER BY name LIMIT %s OFFSET %s"
                params.extend([limit, offset])
                
                cur.execute(query, params)
                venues = []
                for row in cur.fetchall():
                    venues.append(VenueResponse(
                        id=row[0],
                        name=row[1],
                        city=row[2],
                        state=row[3],
                        latitude=row[4],
                        longitude=row[5]
                    ))
                
                return venues
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")

@app.get("/api/v1/venues/{venue_id}", response_model=VenueDetailResponse)
def get_venue_detail(venue_id: int):
    """Get detailed information about a specific venue."""
    try:
        with get_db_connection() as conn:
            with conn.cursor() as cur:
                # Get venue details
                cur.execute("""
                    SELECT v.id, v.name, v.address_line1, v.city, v.state, v.postal_code,
                           v.latitude, v.longitude, v.tz_name,
                           COUNT(e.id) as total_events
                    FROM venue v
                    LEFT JOIN event_instance e ON v.id = e.venue_id
                    WHERE v.id = %s
                    GROUP BY v.id, v.name, v.address_line1, v.city, v.state, v.postal_code,
                             v.latitude, v.longitude, v.tz_name
                """, (venue_id,))
                
                venue_row = cur.fetchone()
                if not venue_row:
                    raise HTTPException(status_code=404, detail=f"Venue {venue_id} not found")
                
                return VenueDetailResponse(
                    id=venue_row[0],
                    name=venue_row[1],
                    address_line1=venue_row[2],
                    city=venue_row[3],
                    state=venue_row[4],
                    postal_code=venue_row[5],
                    latitude=venue_row[6],
                    longitude=venue_row[7],
                    tz_name=venue_row[8],
                    total_events=venue_row[9]
                )
                
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")

@app.get("/api/v1/sites/{site_slug}/events", response_model=List[EventResponse])
def list_events(
    site_slug: str,
    start_date: Optional[date] = Query(None, description="Filter events starting from this date (UTC)"),
    end_date: Optional[date] = Query(None, description="Filter events starting before this date (UTC)"),
    venue_id: Optional[int] = Query(None, description="Filter events by venue ID"),
    artist_search: Optional[str] = Query(None, description="Search events by artist name"),
    title_search: Optional[str] = Query(None, description="Search events by title"),
    price_min: Optional[float] = Query(None, description="Filter events by minimum price"),
    price_max: Optional[float] = Query(None, description="Filter events by maximum price"),
    age_restriction: Optional[str] = Query(None, description="Filter events by age restriction"),
    limit: int = Query(50, ge=1, le=100, description="Maximum number of events to return"),
    offset: int = Query(0, ge=0, description="Number of events to skip")
):
    """List events for a specific site with advanced filtering and pagination."""
    try:
        with get_db_connection() as conn:
            with conn.cursor() as cur:
                # First get the site_id
                cur.execute("SELECT id FROM site WHERE site_slug = %s", (site_slug,))
                site_result = cur.fetchone()
                if not site_result:
                    raise HTTPException(status_code=404, detail=f"Site '{site_slug}' not found")
                
                site_id = site_result[0]
                
                # Build the query with optional filters
                query = """
                    SELECT e.id, e.title, e.artist_name, e.starts_at_utc, e.ends_at_utc,
                           v.name as venue_name, e.price_min, e.price_max, e.currency,
                           e.ticket_url, e.age_restriction
                    FROM event_instance e
                    LEFT JOIN venue v ON e.venue_id = v.id
                    WHERE e.site_id = %s
                """
                params = [site_id]
                
                if start_date:
                    query += " AND e.starts_at_utc >= %s"
                    params.append(datetime.combine(start_date, datetime.min.time()))
                
                if end_date:
                    query += " AND e.starts_at_utc < %s"
                    params.append(datetime.combine(end_date, datetime.min.time()))
                
                if venue_id:
                    query += " AND e.venue_id = %s"
                    params.append(venue_id)
                
                if artist_search:
                    query += " AND e.artist_name ILIKE %s"
                    params.append(f"%{artist_search}%")
                
                if title_search:
                    query += " AND e.title ILIKE %s"
                    params.append(f"%{title_search}%")
                
                if price_min is not None:
                    query += " AND (e.price_max >= %s OR e.price_max IS NULL)"
                    params.append(price_min)
                
                if price_max is not None:
                    query += " AND (e.price_min <= %s OR e.price_min IS NULL)"
                    params.append(price_max)
                
                if age_restriction:
                    query += " AND e.age_restriction = %s"
                    params.append(age_restriction)
                
                query += " ORDER BY e.starts_at_utc LIMIT %s OFFSET %s"
                params.extend([limit, offset])
                
                cur.execute(query, params)
                events = []
                for row in cur.fetchall():
                    events.append(EventResponse(
                        id=row[0],
                        title=row[1],
                        artist_name=row[2],
                        starts_at_utc=row[3].isoformat() if row[3] else None,
                        ends_at_utc=row[4].isoformat() if row[4] else None,
                        venue_name=row[5] or "Unknown Venue",
                        price_min=row[6],
                        price_max=row[7],
                        currency=row[8] or "USD",
                        ticket_url=row[9],
                        age_restriction=row[10]
                    ))
                
                return events
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")

@app.get("/api/v1/events/{event_id}", response_model=EventDetailResponse)
def get_event_detail(event_id: int):
    """Get detailed information about a specific event including source attribution."""
    try:
        with get_db_connection() as conn:
            with conn.cursor() as cur:
                # Get event details
                cur.execute("""
                    SELECT e.id, e.title, e.artist_name, e.starts_at_utc, e.ends_at_utc,
                           v.name as venue_name, e.venue_id, e.price_min, e.price_max, e.currency,
                           e.ticket_url, e.age_restriction, e.is_cancelled
                    FROM event_instance e
                    LEFT JOIN venue v ON e.venue_id = v.id
                    WHERE e.id = %s
                """, (event_id,))
                
                event_row = cur.fetchone()
                if not event_row:
                    raise HTTPException(status_code=404, detail=f"Event {event_id} not found")
                
                # Get source attribution
                cur.execute("""
                    SELECT s.name as source_name, s.url as source_url, esl.external_id, esl.source_url,
                           esl.raw_data, ir.started_at as ingest_time
                    FROM event_source_link esl
                    JOIN source s ON esl.source_id = s.id
                    LEFT JOIN ingest_run ir ON esl.ingest_run_id = ir.id
                    WHERE esl.event_instance_id = %s
                    ORDER BY s.name
                """, (event_id,))
                
                sources = []
                for source_row in cur.fetchall():
                    sources.append({
                        "source_name": source_row[0],
                        "source_url": source_row[1],
                        "external_id": source_row[2],
                        "event_url": source_row[3],
                        "raw_data": source_row[4],
                        "ingest_time": source_row[5].isoformat() if source_row[5] else None
                    })
                
                return EventDetailResponse(
                    id=event_row[0],
                    title=event_row[1],
                    artist_name=event_row[2],
                    starts_at_utc=event_row[3].isoformat() if event_row[3] else None,
                    ends_at_utc=event_row[4].isoformat() if event_row[4] else None,
                    venue_name=event_row[5] or "Unknown Venue",
                    venue_id=event_row[6],
                    price_min=event_row[7],
                    price_max=event_row[8],
                    currency=event_row[9] or "USD",
                    ticket_url=event_row[10],
                    age_restriction=event_row[11],
                    is_cancelled=event_row[12],
                    sources=sources
                )
                
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")

@app.get("/api/v1/search", response_model=SearchResponse)
def search_events_and_venues(
    q: str = Query(..., description="Search query for events and venues"),
    site_slug: Optional[str] = Query(None, description="Limit search to specific site"),
    limit: int = Query(20, ge=1, le=100, description="Maximum number of results to return"),
    offset: int = Query(0, ge=0, description="Number of results to skip")
):
    """Search across events and venues with a single query."""
    try:
        with get_db_connection() as conn:
            with conn.cursor() as cur:
                # Build search query
                search_query = f"%{q}%"
                
                # Search events
                event_query = """
                    SELECT e.id, e.title, e.artist_name, e.starts_at_utc, e.ends_at_utc,
                           v.name as venue_name, e.price_min, e.price_max, e.currency,
                           e.ticket_url, e.age_restriction
                    FROM event_instance e
                    LEFT JOIN venue v ON e.venue_id = v.id
                    WHERE (e.title ILIKE %s OR e.artist_name ILIKE %s)
                """
                event_params = [search_query, search_query]
                
                if site_slug:
                    event_query += " AND e.site_id = (SELECT id FROM site WHERE site_slug = %s)"
                    event_params.append(site_slug)
                
                event_query += " ORDER BY e.starts_at_utc LIMIT %s OFFSET %s"
                event_params.extend([limit, offset])
                
                cur.execute(event_query, event_params)
                events = []
                for row in cur.fetchall():
                    events.append(EventResponse(
                        id=row[0],
                        title=row[1],
                        artist_name=row[2],
                        starts_at_utc=row[3].isoformat() if row[3] else None,
                        ends_at_utc=row[4].isoformat() if row[4] else None,
                        venue_name=row[5] or "Unknown Venue",
                        price_min=row[6],
                        price_max=row[7],
                        currency=row[8] or "USD",
                        ticket_url=row[9],
                        age_restriction=row[10]
                    ))
                
                # Search venues
                venue_query = """
                    SELECT v.id, v.name, v.city, v.state, v.latitude, v.longitude
                    FROM venue v
                    WHERE v.name ILIKE %s
                """
                venue_params = [search_query]
                
                if site_slug:
                    venue_query += " AND v.site_id = (SELECT id FROM site WHERE site_slug = %s)"
                    venue_params.append(site_slug)
                
                venue_query += " ORDER BY v.name LIMIT %s OFFSET %s"
                venue_params.extend([limit, offset])
                
                cur.execute(venue_query, venue_params)
                venues = []
                for row in cur.fetchall():
                    venues.append(VenueResponse(
                        id=row[0],
                        name=row[1],
                        city=row[2],
                        state=row[3],
                        latitude=row[4],
                        longitude=row[5]
                    ))
                
                # Get total counts for pagination
                cur.execute("SELECT COUNT(*) FROM event_instance WHERE title ILIKE %s OR artist_name ILIKE %s", 
                          [search_query, search_query])
                total_events = cur.fetchone()[0]
                
                cur.execute("SELECT COUNT(*) FROM venue WHERE name ILIKE %s", [search_query])
                total_venues = cur.fetchone()[0]
                
                return SearchResponse(
                    events=events,
                    venues=venues,
                    total_events=total_events,
                    total_venues=total_venues,
                    query=q
                )
                
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")
