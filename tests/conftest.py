import os
import asyncio
import pytest
from pathlib import Path
from dotenv import load_dotenv

# Load .env so DATABASE_URL is available for tests
load_dotenv(dotenv_path=Path(__file__).resolve().parents[1] / ".env")

# FastAPI app import
# Expecting api/main.py to expose `app`
from api.main import app

@pytest.fixture(scope="session")
def event_loop():
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()

@pytest.fixture(scope="session")
def fastapi_app():
    return app
