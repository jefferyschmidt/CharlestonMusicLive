import os
import psycopg
import pytest

def test_core_tables_exist():
    url = os.getenv("DATABASE_URL")
    if not url:
        pytest.skip("DATABASE_URL not set")

    with psycopg.connect(url) as conn:
        cur = conn.cursor()
        cur.execute("""
            SELECT table_name
            FROM information_schema.tables
            WHERE table_schema='public'
            ORDER BY table_name
        """)
        names = {r[0] for r in cur.fetchall()}

    # V001
    assert "site" in names
    assert "source" in names
    assert "ingest_run" in names
    # V002
    assert "venue" in names
    assert "event_instance" in names
    assert "event_source_link" in names
    assert "raw_artifact" in names
    assert "geocode_cache" in names
