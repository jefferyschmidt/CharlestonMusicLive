# Architectural Analysis

The MusicLive architecture shows a solid foundation with clear separation of concerns between data collection, extraction, and API serving. The system follows a modular approach with well-defined interfaces for extractors and a comprehensive API layer built with FastAPI.

Key strengths:
- Clear separation between crawling, extraction, and API components
- Well-defined data models with appropriate typing
- Comprehensive API endpoints with proper filtering and pagination
- Structured database schema with appropriate relationships

Areas for improvement:
1. **Error handling and resilience**: The current architecture lacks comprehensive error handling and retry mechanisms for crawlers.
2. **Monitoring and observability**: Limited instrumentation for tracking crawler performance and data quality.
3. **Extraction pipeline**: The extraction process could benefit from a more formalized pipeline with validation stages.
4. **Caching strategy**: No evident caching strategy for API responses or geocoding results.
5. **Asynchronous processing**: Limited use of asynchronous patterns for crawling and processing.
6. **Testing infrastructure**: No clear testing strategy visible in the provided code.
7. **Configuration management**: Source configurations are stored in the database but lack versioning or change tracking.

# Design Patterns

The codebase should continue to follow and enhance these patterns:

1. **Interface Segregation**: The `Extractor` interface is well-defined. Continue this pattern for other components like crawlers and validators.

2. **Repository Pattern**: Implement a formal repository layer to abstract database operations from business logic.

3. **Factory Pattern**: Create factories for extractors and crawlers based on configuration.

4. **Strategy Pattern**: Use for different parsing strategies (HTML, JSON, JavaScript-rendered content).

5. **Decorator Pattern**: Apply for cross-cutting concerns like logging, metrics, and retries.

6. **Command Pattern**: For scheduling and executing crawl jobs.

7. **Observer Pattern**: For monitoring and alerting on crawler events.

8. **Circuit Breaker Pattern**: To handle failures when crawling external sites.

9. **Dependency Injection**: For better testability and component decoupling.

10. **Unit of Work**: For managing database transactions.

# Implementation Guidance

1. **Crawler Infrastructure**:
```python
from dataclasses import dataclass
from enum import Enum
from typing import Optional, Dict, Any, List
import aiohttp
import asyncio
from structlog import get_logger

logger = get_logger()

class CrawlerType(Enum):
    HTTP = "http"
    PLAYWRIGHT = "playwright"
    API = "api"

@dataclass
class CrawlResult:
    source_id: int
    url: str
    content: str
    status_code: int
    headers: Dict[str, str]
    crawl_time_ms: int
    error: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None

class BaseCrawler:
    """Base crawler interface that all crawler implementations must follow."""
    
    def __init__(self, source_id: int, url: str, politeness_delay_ms: int = 1000, 
                 respect_robots_txt: bool = True, headers: Optional[Dict[str, str]] = None):
        self.source_id = source_id
        self.url = url
        self.politeness_delay_ms = politeness_delay_ms
        self.respect_robots_txt = respect_robots_txt
        self.headers = headers or {
            "User-Agent": "MusicLive Crawler/0.1 (+https://musiclive.example.com/about/robots)"
        }
    
    async def crawl(self) -> CrawlResult:
        """Crawl the URL and return the result."""
        raise NotImplementedError

class HttpCrawler(BaseCrawler):
    """Simple HTTP crawler using aiohttp."""
    
    async def crawl(self) -> CrawlResult:
        start_time = asyncio.get_event_loop().time()
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(self.url, headers=self.headers, 
                                      timeout=aiohttp.ClientTimeout(total=30)) as response:
                    content = await response.text()
                    end_time = asyncio.get_event_loop().time()
                    crawl_time_ms = int((end_time - start_time) * 1000)
                    
                    return CrawlResult(
                        source_id=self.source_id,
                        url=self.url,
                        content=content,
                        status_code=response.status,
                        headers=dict(response.headers),
                        crawl_time_ms=crawl_time_ms
                    )
        except Exception as e:
            end_time = asyncio.get_event_loop().time()
            crawl_time_ms = int((end_time - start_time) * 1000)
            logger.error("Crawl error", url=self.url, error=str(e))
            return CrawlResult(
                source_id=self.source_id,
                url=self.url,
                content="",
                status_code=0,
                headers={},
                crawl_time_ms=crawl_time_ms,
                error=str(e)
            )

class CrawlerFactory:
    """Factory for creating crawlers based on configuration."""
    
    @staticmethod
    def create_crawler(source_id: int, url: str, crawler_type: CrawlerType, 
                      politeness_delay_ms: int = 1000, respect_robots_txt: bool = True,
                      headers: Optional[Dict[str, str]] = None) -> BaseCrawler:
        if crawler_type == CrawlerType.HTTP:
            return HttpCrawler(source_id, url, politeness_delay_ms, respect_robots_txt, headers)
        elif crawler_type == CrawlerType.PLAYWRIGHT:
            # Implement PlaywrightCrawler for JavaScript-rendered content
            raise NotImplementedError("Playwright crawler not implemented yet")
        elif crawler_type == CrawlerType.API:
            # Implement ApiCrawler for API endpoints
            raise NotImplementedError("API crawler not implemented yet")
        else:
            raise ValueError(f"Unknown crawler type: {crawler_type}")
```

2. **Extraction Pipeline**:
```python
from dataclasses import dataclass
from typing import List, Optional, Dict, Any, Callable
from datetime import datetime
import re

@dataclass
class ValidationResult:
    is_valid: bool
    errors: List[str]

class ValidationError(Exception):
    """Exception raised for validation errors."""
    pass

class ExtractorPipeline:
    """Pipeline for processing extraction results with validation and enrichment."""
    
    def __init__(self):
        self.validators: List[Callable[[ExtractResult], ValidationResult]] = []
        self.enrichers: List[Callable[[ExtractResult], ExtractResult]] = []
    
    def add_validator(self, validator: Callable[[ExtractResult], ValidationResult]):
        """Add a validator to the pipeline."""
        self.validators.append(validator)
        return self
    
    def add_enricher(self, enricher: Callable[[ExtractResult], ExtractResult]):
        """Add an enricher to the pipeline."""
        self.enrichers.append(enricher)
        return self
    
    def process(self, extract_results: List[ExtractResult]) -> List[ExtractResult]:
        """Process extraction results through the pipeline."""
        valid_results = []
        
        for result in extract_results:
            # Run all validators
            validation_errors = []
            for validator in self.validators:
                validation = validator(result)
                if not validation.is_valid:
                    validation_errors.extend(validation.errors)
            
            if validation_errors:
                # Log validation errors but continue processing
                continue
            
            # Run all enrichers
            enriched_result = result
            for enricher in self.enrichers:
                enriched_result = enricher(enriched_result)
            
            valid_results.append(enriched_result)
        
        return valid_results

# Example validators and enrichers
def validate_required_fields(result: ExtractResult) -> ValidationResult:
    """Validate that all required fields are present."""
    errors = []
    
    if not result.site_slug:
        errors.append("site_slug is required")
    if not result.venue_name:
        errors.append("venue_name is required")
    if not result.title:
        errors.append("title is required")
    if not result.starts_at_utc:
        errors.append("starts_at_utc is required")
    
    return ValidationResult(is_valid=len(errors) == 0, errors=errors)

def validate_dates(result: ExtractResult) -> ValidationResult:
    """Validate that dates are in the correct format and logical."""
    errors = []
    
    try:
        starts_at = datetime.fromisoformat(result.starts_at_utc.replace('Z', '+00:00'))
        
        if result.ends_at_utc:
            ends_at = datetime.fromisoformat(result.ends_at_utc.replace('Z', '+00:00'))
            if ends_at <= starts_at:
                errors.append("ends_at_utc must be after starts_at_utc")
        
        if result.doors_time_utc:
            doors_time = datetime.fromisoformat(result.doors_time_utc.replace('Z', '+00:00'))
            if doors_time > starts_at:
                errors.append("doors_time_utc must be before or equal to starts_at_utc")
    except ValueError:
        errors.append("Invalid date format")
    
    return ValidationResult(is_valid=len(errors) == 0, errors=errors)

def enrich_artist_name(result: ExtractResult) -> ExtractResult:
    """Extract artist name from title if not provided."""
    if not result.artist_name and result.title:
        # Common patterns: "Artist Name - Event Title" or "Event Title with Artist Name"
        if " - " in result.title:
            parts = result.title.split(" - ", 1)
            result.artist_name = parts[0].strip()
        
    return result
```

3. **Repository Pattern Implementation**:
```python
from typing import List, Optional, Dict, Any
from datetime import datetime
import psycopg
from psycopg.rows import dict_row

class EventRepository:
    """Repository for event-related database operations."""
    
    def __init__(self, db_connection_factory):
        self.db_connection_factory = db_connection_factory
    
    async def get_event_by_id(self, event_id: int) -> Optional[Dict[str, Any]]:
        """Get an event by ID."""
        query = """
            SELECT e.*, v.name as venue_name
            FROM event_instance e
            LEFT JOIN venue v ON e.venue_id = v.id
            WHERE e.id = %s
        """
        
        async with self.db_connection_factory() as conn:
            async with conn.cursor(row_factory=dict_row) as cur:
                await cur.execute(query, (event_id,))
                return await cur.fetchone()
    
    async def find_similar_event(self, venue_id: int, title: str, 
                                starts_at_utc: datetime) -> Optional[Dict[str, Any]]:
        """Find a similar event at the same venue with similar title and time."""
        query = """
            SELECT id, title, starts_at_utc
            FROM event_instance
            WHERE venue_id = %s
            AND (
                -- Same title or very similar
                title ILIKE %s
                -- Or similar time (within 2 hours)
                OR (ABS(EXTRACT(EPOCH FROM (starts_at_utc - %s)) / 3600) < 2)
            )
            ORDER BY 
                -- Prioritize exact title matches
                CASE WHEN LOWER(title) = LOWER(%s) THEN 0 ELSE 1 END,
                -- Then prioritize by time proximity
                ABS(EXTRACT(EPOCH FROM (starts_at_utc - %s)))
            LIMIT 1
        """
        
        async with self.db_connection_factory() as conn:
            async with conn.cursor(row_factory=dict_row) as cur:
                await cur.execute(query, (
                    venue_id, 
                    f"%{title}%", 
                    starts_at_utc, 
                    title.lower(),
                    starts_at_utc
                ))
                return await cur.fetchone()
    
    async def create_event(self, event_data: Dict[str, Any]) -> int:
        """Create a new event and return its ID."""
        query = """
            INSERT INTO event_instance (
                site_id, venue_id, title, artist_name, starts_at_utc, ends_at_utc,
                doors_time_utc, price_min, price_max, currency, ticket_url,
                age_restriction, is_cancelled
            ) VALUES (
                %(site_id)s, %(venue_id)s, %(title)s, %(artist_name)s, %(starts_at_utc)s, 
                %(ends_at_utc)s, %(doors_time_utc)s, %(price_min)s, %(price_max)s, 
                %(currency)s, %(ticket_url)s, %(age_restriction)s, %(is_cancelled)s
            )
            RETURNING id
        """
        
        async with self.db_connection_factory() as conn:
            async with conn.cursor() as cur:
                await cur.execute(query, event_data)
                event_id = await cur.fetchone()
                await conn.commit()
                return event_id[0]
    
    async def update_event(self, event_id: int, event_data: Dict[str, Any]) -> bool:
        """Update an existing event."""
        # Build dynamic update query based on provided fields
        set_clauses = []
        params = {"id": event_id}
        
        for key, value in event_data.items():
            if key != "id":  # Skip the ID field
                set_clauses.append(f"{key} = %({key})s")
                params[key] = value
        
        if not set_clauses:
            return False  # Nothing to update
        
        set_clause = ", ".join(set_clauses)
        query = f"""
            UPDATE event_instance
            SET {set_clause}, updated_at = now()
            WHERE id = %(id)s
        """
        
        async with self.db_connection_factory() as conn:
            async with conn.cursor() as cur:
                await cur.execute(query, params)
                rows_affected = cur.rowcount
                await conn.commit()
                return rows_affected > 0
```

# Scalability Considerations

1. **Crawler Scalability**:
   - Implement a distributed crawler system using a task queue (e.g., Celery, AWS SQS)
   - Add rate limiting per domain to avoid overwhelming venue websites
   - Use a crawl frontier to manage URLs and crawl priorities
   - Consider containerization for horizontal scaling of crawlers

2. **Database Scalability**:
   - Implement connection pooling for database connections
   - Add read replicas for API queries to reduce load on the primary database
   - Consider time-based partitioning for event data as it grows
   - Implement efficient indexing strategies for common query patterns

3. **API Performance**:
   - Add response caching for frequently accessed endpoints
   - Implement pagination for all list endpoints
   - Consider GraphQL for more flexible querying patterns
   - Add compression for API responses

4. **Monitoring and Observability**:
   - Implement structured logging with correlation IDs
   - Add metrics collection for crawler performance
   - Set up alerting for crawler failures and data quality issues
   - Create dashboards for system health monitoring

5. **Fault Tolerance**:
   - Implement retry mechanisms with exponential backoff for crawlers
   - Add circuit breakers for external dependencies
   - Implement graceful degradation for API endpoints
