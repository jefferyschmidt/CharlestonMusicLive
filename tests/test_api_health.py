import pytest
from httpx import AsyncClient, ASGITransport

@pytest.mark.asyncio
async def test_root_status_ok(fastapi_app):
    transport = ASGITransport(app=fastapi_app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        resp = await ac.get("/")
    assert resp.status_code == 200

    # Try JSON first; if not JSON, fall back to HTML/text check
    ctype = resp.headers.get("content-type", "")
    if "application/json" in ctype:
        data = resp.json()
        assert str(data.get("status", "")).lower() == "ok"
    else:
        body = resp.text.lower()
        assert "status" in body and "ok" in body
