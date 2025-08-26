# Architectural Analysis

The MusicLive architecture demonstrates a solid foundation with clear separation of concerns between data collection, extraction, and API serving. The system follows a modular approach with well-defined interfaces for extractors and a comprehensive API layer built with FastAPI.

Key strengths:
- Clear extractor interface pattern for parsing different venue sources
- Well-structured API endpoints with comprehensive filtering options
- Robust data models with appropriate relationships
- Thoughtful database schema design with proper indexing

Areas for improvement:
1. **Crawler Infrastructure**: The crawler implementation details are not fully visible, but there appears to be a need for a more robust crawler management system with retry logic, error handling, and monitoring.
2. **Dependency Injection**: The codebase could benefit from a more explicit dependency injection pattern, particularly for database connections.
3. **Asynchronous Processing**: While FastAPI supports async, the database operations appear to be synchronous, which could limit scalability.
4. **Caching Strategy**: No evident caching strategy for frequently accessed data or geocoding results.
5. **Observability**: Limited instrumentation for monitoring and observability beyond basic admin status.
6. **Testing Framework**: Testing approach is not clearly defined in the provided code.

# Design Patterns

1. **Repository Pattern**: Implement a repository layer to abstract database operations from business logic. This would improve testability and separation of concerns.

```python
# Example repository pattern implementation
class VenueRepository:
    def __init__(self, db_connection):
        self.db_connection = db_connection
        
    async def get_by_id(self, venue_id: int) -> Optional[VenueDetailResponse]:
        # Implementation
        pass
        
    async def search(self, site_id: int, search_term: Optional[str] = None, 
                    limit: int = 50, offset: int = 0) -> List[VenueResponse]:
        # Implementation
        pass
```

2. **Service Layer Pattern**: Add a service layer between API endpoints and repositories to encapsulate business logic.

```python
class EventService:
    def __init__(self, event_repository, venue_repository):
        self.event_repository = event_repository
        self.venue_repository = venue_repository
        
    async def get_events_by_site(self, site_slug: str, filters: dict) -> List[EventResponse]:
        # Business logic for filtering and retrieving events
        pass
```

3. **Unit of Work Pattern**: Manage database transactions consistently.

```python
class UnitOfWork:
    def __init__(self, connection_factory):
        self.connection_factory = connection_factory
        
    async def __aenter__(self):
        self.connection = await self.connection_factory()
        self.transaction = self.connection.transaction()
        await self.transaction.start()
        return self
        
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if exc_type:
            await self.transaction.rollback()
        else:
            await self.transaction.commit()
        await self.connection.close()
```

4. **Factory Pattern**: For creating extractors based on source configuration.

```python
class ExtractorFactory:
    @staticmethod
    def create_extractor(source_config: SourceConfig) -> Extractor:
        if source_config.parser_type == "music_farm":
            return MusicFarmExtractor(source_config.site_slug, source_config.url)
        elif source_config.parser_type == "pour_house":
            return PourHouseExtractor(source_config.site_slug, source_config.url)
        # Add more extractors as needed
        else:
            raise ValueError(f"Unknown parser type: {source_config.parser_type}")
```

5. **Strategy Pattern**: For different crawling strategies (JavaScript rendering, simple HTTP, etc.)

```python
class CrawlerStrategy:
    async def fetch(self, url: str, options: dict) -> str:
        raise NotImplementedError()

class SimpleHttpCrawlerStrategy(CrawlerStrategy):
    async def fetch(self, url: str, options: dict) -> str:
        # Implementation using httpx or aiohttp
        pass

class PlaywrightCrawlerStrategy(CrawlerStrategy):
    async def fetch(self, url: str, options: dict) -> str:
        # Implementation using Playwright for JavaScript rendering
        pass
```

# Implementation Guidance

1. **Asynchronous Database Operations**:
   Convert database operations to use asynchronous patterns with `asyncpg` instead of `psycopg`:

```python
import asyncpg

async def get_db_pool():
    """Get database connection pool."""
    database_url = os.getenv("DATABASE_URL")
    if not database_url:
        raise HTTPException(status_code=500, detail="Database not configured")
    return await asyncpg.create_pool(database_url)

# In FastAPI dependency
async def get_db():
    pool = await get_db_pool()
    async with pool.acquire() as connection:
        yield connection
```

2. **Crawler Implementation**:
   Implement a robust crawler with proper rate limiting and error handling:

```python
class Crawler:
    def __init__(self, strategy: CrawlerStrategy, politeness_delay_ms: int = 1000):
        self.strategy = strategy
        self.politeness_delay_ms = politeness_delay_ms
        self.last_request_time = 0
        
    async def fetch(self, url: str, options: dict = None) -> str:
        # Respect politeness delay
        now = time.time() * 1000
        time_since_last_request = now - self.last_request_time
        if time_since_last_request < self.politeness_delay_ms:
            await asyncio.sleep((self.politeness_delay_ms - time_since_last_request) / 1000)
            
        try:
            content = await self.strategy.fetch(url, options or {})
            self.last_request_time = time.time() * 1000
            return content
        except Exception as e:
            # Log error and potentially retry
            logger.error(f"Error fetching {url}: {str(e)}")
            raise
```

3. **Caching Implementation**:
   Add Redis-based caching for frequently accessed data:

```python
import aioredis

class CacheService:
    def __init__(self, redis_url: str):
        self.redis = aioredis.from_url(redis_url)
        
    async def get(self, key: str) -> Optional[str]:
        return await self.redis.get(key)
        
    async def set(self, key: str, value: str, ttl_seconds: int = 3600):
        await self.redis.set(key, value, ex=ttl_seconds)
        
    async def invalidate(self, key: str):
        await self.redis.delete(key)
```

4. **Structured Logging**:
   Enhance the existing structlog implementation:

```python
import structlog
import logging
import time

def setup_logging():
    logging.basicConfig(level=logging.INFO)
    
    structlog.configure(
        processors=[
            structlog.stdlib.filter_by_level,
            structlog.stdlib.add_logger_name,
            structlog.stdlib.add_log_level,
            structlog.stdlib.PositionalArgumentsFormatter(),
            structlog.processors.TimeStamper(fmt="iso"),
            structlog.processors.StackInfoRenderer(),
            structlog.processors.format_exc_info,
            structlog.processors.UnicodeDecoder(),
            structlog.processors.JSONRenderer()
        ],
        context_class=dict,
        logger_factory=structlog.stdlib.LoggerFactory(),
        wrapper_class=structlog.stdlib.BoundLogger,
        cache_logger_on_first_use=True,
    )
    
    return structlog.get_logger()

logger = setup_logging()
```

5. **Dependency Injection Container**:
   Implement a simple DI container:

```python
class Container:
    def __init__(self):
        self._services = {}
        
    def register(self, service_type, factory):
        self._services[service_type] = factory
        
    def resolve(self, service_type):
        factory = self._services.get(service_type)
        if not factory:
            raise ValueError(f"No factory registered for {service_type}")
        return factory(self)
```

# Scalability Considerations

1. **Database Connection Pooling**:
   Implement proper connection pooling to handle concurrent requests efficiently:

```python
# In app startup
app.state.db_pool = await asyncpg.create_pool(
    os.getenv("DATABASE_URL"),
    min_size=5,
    max_size=20
)

# In app shutdown
await app.state.db_pool.close()

# In dependency
async def get_db_conn():
    async with app.state.db_pool.acquire() as conn:
        yield conn
```

2. **Background Tasks for Crawling**:
   Move crawling to background tasks using a task queue like Celery or a simpler solution with asyncio:

```python
from fastapi.background import BackgroundTasks

@app.post("/admin/sources/{source_id}/crawl")
async def trigger_crawl(source_id: int, background_tasks: BackgroundTasks):
    background_tasks.add_task(crawl_source, source_id)
    return {"status": "crawl scheduled"}

async def crawl_source(source_id: int):
    # Implementation
    pass
```

3. **Horizontal Scaling**:
   Design the system to be stateless for horizontal scaling:
   - Move session state to Redis
   - Use distributed locking for crawler coordination
   - Implement proper database connection management

4. **Caching Strategy**:
   Implement multi-level caching:
   - In-memory caching for hot data
   - Redis for distributed caching
   - HTTP caching headers for API responses

```python
from fastapi import Response

@app.get("/api/v1/venues/{venue_id}", response_model=VenueDetailResponse)
async def get_venue_detail(venue_id: int, response: Response):
    # Set cache headers
    response.headers["Cache-Control"] = "public, max-age=300"  # 5 minutes
    # Rest of implementation
```

5. **Rate Limiting**:
   Implement rate limiting for API endpoints:

```python
from fastapi import Depends, HTTPException, Request
import time
from typing import Dict, Tuple

class RateLimiter:
    def __init__(self, requests_per_minute: int = 60):
        self.requests_per_minute = requests_per_minute
        self.clients: Dict[str, Tuple[int, float]] = {}
        
    async def __call__(self, request: Request):
        client_ip = request.client.host
        current_time = time.time()
        
        if client_ip in self.clients:
            count, start_time = self.clients[client_ip]
            if current_time - start_time > 60:
                # Reset if more than a minute has passed
                self.clients[client_ip] = (1, current_time)
            elif count >= self.requests_per_minute:
                raise HTTPException(status_code=429, detail="Too many requests")
            else:
                self.clients[client_ip] = (count + 1, start_time)
        else:
            self.clients[client_ip] = (1, current_time)

# Usage in endpoint
@app.get("/api/v1/search", dependencies=[Depends(RateLimiter(requests_per_minute=30))])
async def search_events_and_venues():
    # Implementation
```

# Code Review

1. **Database Connection Management**:
   The current implementation creates a new connection for each request, which is inefficient:

```python
# Current approach
def get_db_connection():
    database_url = os.getenv("DATABASE_URL")
    if not database_url:
        raise HTTPException(status_code=500, detail="Database not configured")
    return psycopg.connect(database_url)

# Recommended approach
async def get_db_pool():
    if not hasattr(app.state, "db_pool"):
        app.state.db_pool = await asyncpg.create_pool(os.getenv("DATABASE_URL"))
    return app.state.db_pool

async def get_db():
    pool = await get_db_pool()
    async with pool.acquire() as conn:
        yield conn
```

2. **Error Handling**:
   The error handling in API endpoints could be more specific:

```python
# Current approach
@app.get("/api/v1/venues/{venue_id}")
def get_venue_detail(venue_id: int):
    try:
        # Implementation
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")

# Recommended approach
@app.get("/api/v1/venues/{venue_id}")
async def get_venue_detail(venue_id: int):
    try:
        # Implementation
    except asyncpg.PostgresError as e:
        logger.error("Database error", venue_id=venue_id, error=str(e))
        raise HTTPException(status_code=500, detail="Database error occurred")
    except KeyError:
        raise HTTPException(status_code=404, detail=f"Venue {venue_id} not found")
    except Exception as e:
        logger.exception("Unexpected error", venue_id=venue_id)
        raise HTTPException(status_code=500, detail="An unexpected error occurred")
```

3. **Extractor Interface**:
   The Extractor interface is well-designed but could benefit from async support:

```python
class Extractor:
    """Interface every venue/source extractor must implement."""

    def __init__(self, site_slug: str, source_url: str, tz_name: str = "America/New_York") -> None:
        self.site_slug = site_slug
        self.source_url = source_url
        self.tz_name = tz_name

    async def parse(self, html: str) -> List[ExtractResult]:
        """Parse HTML (or JSON string) and return normalized events.
        Must be deterministic and side-effect free. No network calls here.
        """
        raise NotImplementedError
```

4. **API Response Models**:
   Consider using Pydantic models instead of dataclasses for better validation:

```python
from pydantic import BaseModel, Field
from typing import List, Optional
from datetime import datetime

class EventResponse(BaseModel):
    id: int
    title: str
    artist_name: Optional[str] = None
    starts_at_utc: datetime
    ends_at_utc: Optional[datetime] = None
    venue_name: str
    price_min: Optional[float] = None
    price_max: Optional[float] = None
    currency: str = "USD"
    ticket_url: Optional[str] = None
    age_restriction: Optional[str] = None
    
    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }
```

5. **SQL Injection Prevention**:
   While the code uses parameterized queries, ensure consistent usage throughout:

```python
# Ensure all dynamic SQL is properly parameterized
query = """
    SELECT id, name, city, state, latitude, longitude
    FROM venue 
    WHERE site_id = $1
"""
if search:
    query += " AND name ILIKE $2"
    params.append(f"%{search}%")
    
query += " ORDER BY name LIMIT $3 OFFSET $4"
params.extend([limit, offset])
```

# Next Steps

1. **Refactor Database Layer**:
   - Implement the Repository pattern
   - Convert to async database operations with asyncpg
   - Add proper connection pooling

2. **Enhance Crawler Infrastructure**:
   - Implement the Strategy pattern for different crawling methods
   - Add robust error handling and retry logic
