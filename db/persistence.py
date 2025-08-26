from __future__ import annotations

import os
from dataclasses import dataclass
from datetime import datetime
from typing import Any, Dict, Optional, Tuple

import psycopg


@dataclass
class DbIds:
    site_id: int
    source_id: int


def _database_url() -> str:
    url = os.getenv("DATABASE_URL")
    if not url:
        raise RuntimeError("DATABASE_URL not set")
    return url


def get_connection() -> psycopg.Connection:
    return psycopg.connect(_database_url())


# --- Site / Source ensure helpers ---

def ensure_site(conn: psycopg.Connection, site_slug: str, display_name: Optional[str] = None) -> int:
    display = display_name or site_slug.title()
    with conn.cursor() as cur:
        cur.execute(
            """
            INSERT INTO site (site_slug, display_name)
            VALUES (%s, %s)
            ON CONFLICT (site_slug) DO UPDATE SET display_name = EXCLUDED.display_name
            RETURNING id
            """,
            (site_slug, display,),
        )
        row = cur.fetchone()
        return int(row[0])


def ensure_source(
    conn: psycopg.Connection,
    site_id: int,
    name: str,
    url: str,
    requires_browser: bool = False,
    rate_limit_rps: float = 1.0,
    active: bool = True,
) -> int:
    with conn.cursor() as cur:
        # Try find existing by (site_id, url) then upsert by name
        cur.execute(
            "SELECT id FROM source WHERE site_id=%s AND url=%s",
            (site_id, url),
        )
        row = cur.fetchone()
        if row:
            return int(row[0])
        cur.execute(
            """
            INSERT INTO source (site_id, name, url, requires_browser, rate_limit_rps, active)
            VALUES (%s, %s, %s, %s, %s, %s)
            RETURNING id
            """,
            (site_id, name, url, requires_browser, rate_limit_rps, active),
        )
        return int(cur.fetchone()[0])


# --- Venue upsert ---

def upsert_venue(
    conn: psycopg.Connection,
    site_id: int,
    name: str,
    address_line1: Optional[str] = None,
    address_line2: Optional[str] = None,
    city: Optional[str] = None,
    state: Optional[str] = None,
    postal_code: Optional[str] = None,
    country: str = "US",
    latitude: Optional[float] = None,
    longitude: Optional[float] = None,
    tz_name: str = "America/New_York",
) -> int:
    with conn.cursor() as cur:
        cur.execute(
            """
            INSERT INTO venue (site_id, name, address_line1, address_line2, city, state, postal_code,
                               country, latitude, longitude, tz_name)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            ON CONFLICT (site_id, name) DO UPDATE SET
                address_line1 = EXCLUDED.address_line1,
                address_line2 = EXCLUDED.address_line2,
                city = EXCLUDED.city,
                state = EXCLUDED.state,
                postal_code = EXCLUDED.postal_code,
                country = EXCLUDED.country,
                latitude = EXCLUDED.latitude,
                longitude = EXCLUDED.longitude,
                tz_name = EXCLUDED.tz_name,
                updated_at = now()
            RETURNING id
            """,
            (
                site_id,
                name,
                address_line1,
                address_line2,
                city,
                state,
                postal_code,
                country,
                latitude,
                longitude,
                tz_name,
            ),
        )
        return int(cur.fetchone()[0])


# --- Event instance insert (no natural unique constraint in MVP) ---

def insert_event_instance(
    conn: psycopg.Connection,
    site_id: int,
    venue_id: Optional[int],
    *,
    title: str,
    description: Optional[str],
    artist_name: Optional[str],
    starts_at_utc: datetime,
    ends_at_utc: Optional[datetime],
    tz_name: str,
    doors_time_utc: Optional[datetime],
    price_min: Optional[float],
    price_max: Optional[float],
    currency: str = "USD",
    ticket_url: Optional[str] = None,
    age_restriction: Optional[str] = None,
    is_cancelled: bool = False,
    source_created_at: Optional[datetime] = None,
    source_updated_at: Optional[datetime] = None,
) -> int:
    with conn.cursor() as cur:
        cur.execute(
            """
            INSERT INTO event_instance (
                site_id, venue_id, title, description, artist_name, starts_at_utc, ends_at_utc, tz_name,
                doors_time_utc, price_min, price_max, currency, ticket_url, age_restriction, is_cancelled,
                source_created_at, source_updated_at
            ) VALUES (
                %s, %s, %s, %s, %s, %s, %s, %s,
                %s, %s, %s, %s, %s, %s, %s,
                %s, %s
            ) RETURNING id
            """,
            (
                site_id,
                venue_id,
                title,
                description,
                artist_name,
                starts_at_utc,
                ends_at_utc,
                tz_name,
                doors_time_utc,
                price_min,
                price_max,
                currency,
                ticket_url,
                age_restriction,
                is_cancelled,
                source_created_at,
                source_updated_at,
            ),
        )
        return int(cur.fetchone()[0])


# --- Event source link upsert (unique per (event_instance, source)) ---

def upsert_event_source_link(
    conn: psycopg.Connection,
    event_instance_id: int,
    source_id: int,
    ingest_run_id: Optional[int],
    *,
    external_id: Optional[str],
    source_url: str,
    raw_data: Optional[Dict[str, Any]] = None,
) -> int:
    with conn.cursor() as cur:
        cur.execute(
            """
            INSERT INTO event_source_link (
                event_instance_id, source_id, ingest_run_id, external_id, source_url, raw_data
            ) VALUES (
                %s, %s, %s, %s, %s, %s
            )
            ON CONFLICT (event_instance_id, source_id) DO UPDATE SET
                ingest_run_id = EXCLUDED.ingest_run_id,
                external_id = EXCLUDED.external_id,
                source_url = EXCLUDED.source_url,
                raw_data = COALESCE(EXCLUDED.raw_data, event_source_link.raw_data),
                updated_at = now()
            RETURNING id
            """,
            (
                event_instance_id,
                source_id,
                ingest_run_id,
                external_id,
                source_url,
                psycopg.types.json.Json(raw_data) if raw_data is not None else None,
            ),
        )
        return int(cur.fetchone()[0])
