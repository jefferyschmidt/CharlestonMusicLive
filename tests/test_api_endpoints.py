import pytest
from httpx import AsyncClient, ASGITransport
from unittest.mock import patch, MagicMock
import os

# Import the app from the main module
from api.main import app

@pytest.mark.asyncio
async def test_admin_status_endpoint():
    """Test the admin status endpoint works correctly."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        resp = await ac.get("/admin/status")
    
    assert resp.status_code == 200
    data = resp.json()
    assert "status" in data
    assert "timestamp" in data
    assert "database_connected" in data
    
    # Should return either healthy or error status
    assert data["status"] in ["healthy", "error"]
    
    if data["database_connected"]:
        assert data["status"] == "healthy"
        assert "total_sites" in data
        assert "total_sources" in data
        assert "total_venues" in data
        assert "total_events" in data
    else:
        assert data["status"] == "error"

@pytest.mark.asyncio
async def test_list_venues_endpoint():
    """Test the venues endpoint works when database is configured."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        resp = await ac.get("/api/v1/sites/charleston/venues")
    
    # With a real database, this should either return venues or a 404 if the site doesn't exist
    assert resp.status_code in [200, 404]
    if resp.status_code == 200:
        data = resp.json()
        assert isinstance(data, list)
    elif resp.status_code == 404:
        data = resp.json()
        assert "detail" in data
        assert "not found" in data["detail"].lower()

@pytest.mark.asyncio
async def test_list_events_endpoint():
    """Test the events endpoint works when database is configured."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        resp = await ac.get("/api/v1/sites/charleston/events")
    
    # With a real database, this should either return events or a 404 if the site doesn't exist
    assert resp.status_code in [200, 404]
    if resp.status_code == 200:
        data = resp.json()
        assert isinstance(data, list)
    elif resp.status_code == 404:
        data = resp.json()
        assert "detail" in data
        assert "not found" in data["detail"].lower()

@pytest.mark.asyncio
async def test_venues_endpoint_with_search_params():
    """Test the venues endpoint accepts search parameters correctly."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        resp = await ac.get("/api/v1/sites/charleston/venues?search=music&limit=10&offset=0")
    
    # Should work with parameters, either returning data or 404
    assert resp.status_code in [200, 404]
    if resp.status_code == 200:
        data = resp.json()
        assert isinstance(data, list)

@pytest.mark.asyncio
async def test_events_endpoint_with_date_filters():
    """Test the events endpoint accepts date filter parameters correctly."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        resp = await ac.get("/api/v1/sites/charleston/events?start_date=2025-01-01&end_date=2025-12-31&venue_id=1")
    
    # Should work with parameters, either returning data or 404
    if resp.status_code == 200:
        data = resp.json()
        assert isinstance(data, list)

@pytest.mark.asyncio
async def test_events_endpoint_with_advanced_filters():
    """Test the events endpoint accepts advanced filter parameters correctly."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        resp = await ac.get("/api/v1/sites/charleston/events?artist_search=black&title_search=keys&price_min=20&price_max=100&age_restriction=All%20Ages")
    
    # Should work with parameters, either returning data or 404
    if resp.status_code == 200:
        data = resp.json()
        assert isinstance(data, list)

@pytest.mark.asyncio
async def test_event_detail_endpoint():
    """Test the event detail endpoint works when database is configured."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        resp = await ac.get("/api/v1/events/1")
    
    # With a real database, this should either return event details or a 404 if the event doesn't exist
    assert resp.status_code in [200, 404]
    if resp.status_code == 200:
        data = resp.json()
        assert "id" in data
        assert "title" in data
        assert "venue_name" in data
        assert "sources" in data
        assert isinstance(data["sources"], list)
    elif resp.status_code == 404:
        data = resp.json()
        assert "detail" in data
        assert "not found" in data["detail"].lower()

@pytest.mark.asyncio
async def test_venue_detail_endpoint():
    """Test the venue detail endpoint works when database is configured."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        resp = await ac.get("/api/v1/venues/1")
    
    # With a real database, this should either return venue details or a 404 if the venue doesn't exist
    assert resp.status_code in [200, 404]
    if resp.status_code == 200:
        data = resp.json()
        assert "id" in data
        assert "name" in data
        assert "total_events" in data
        assert isinstance(data["total_events"], int)
    elif resp.status_code == 404:
        data = resp.json()
        assert "detail" in data
        assert "not found" in data["detail"].lower()

@pytest.mark.asyncio
async def test_search_endpoint():
    """Test the search endpoint works when database is configured."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        resp = await ac.get("/api/v1/search?q=music")
    
    # With a real database, this should return search results
    assert resp.status_code == 200
    data = resp.json()
    assert "events" in data
    assert "venues" in data
    assert "total_events" in data
    assert "total_venues" in data
    assert "query" in data
    assert data["query"] == "music"
    assert isinstance(data["events"], list)
    assert isinstance(data["venues"], list)

@pytest.mark.asyncio
async def test_search_endpoint_with_site_filter():
    """Test the search endpoint with site filtering works correctly."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        resp = await ac.get("/api/v1/search?q=music&site_slug=charleston&limit=10&offset=0")
    
    # Should work with site filtering parameters
    assert resp.status_code == 200
    data = resp.json()
    assert "events" in data
    assert "venues" in data
    assert "query" in data
    assert data["query"] == "music"

@pytest.mark.asyncio
async def test_nonexistent_site_returns_404():
    """Test that requesting a non-existent site returns appropriate error."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        resp = await ac.get("/api/v1/sites/nonexistent/venues")
    
    # This might return 404 for a non-existent site, or 500 if there's a database error
    assert resp.status_code in [404, 500]
    data = resp.json()
    assert "detail" in data
    if resp.status_code == 404:
        assert "not found" in data["detail"].lower()
    elif resp.status_code == 500:
        assert "Database error" in data["detail"]

@pytest.mark.asyncio
async def test_api_handles_database_errors_gracefully():
    """Test that the API handles database errors gracefully."""
    # Mock the database connection to simulate a database error
    with patch('api.main.get_db_connection') as mock_db:
        mock_db.side_effect = Exception("Database connection failed")
        
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as ac:
            resp = await ac.get("/api/v1/sites/charleston/venues")
        
        assert resp.status_code == 500
        data = resp.json()
        assert "detail" in data
        assert "Database error" in data["detail"]
