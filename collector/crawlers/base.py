"""
Base crawler interface and data structures.
"""

from dataclasses import dataclass
from enum import Enum
from typing import Optional, Dict, Any, List
from datetime import datetime


class CrawlerType(Enum):
    """Types of crawlers available."""
    HTTP = "http"
    PLAYWRIGHT = "playwright"
    API = "api"


@dataclass
class CrawlResult:
    """Result of a crawling operation."""
    source_id: int
    url: str
    content: str
    status_code: int
    headers: Dict[str, str]
    crawl_time_ms: int
    error: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None
    content_type: Optional[str] = None
    rendered_content: Optional[str] = None  # For JavaScript-rendered content


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
    
    async def _respect_politeness(self):
        """Respect politeness delay between requests."""
        if self.politeness_delay_ms > 0:
            import asyncio
            await asyncio.sleep(self.politeness_delay_ms / 1000.0)
    
    def _extract_domain(self, url: str) -> Optional[str]:
        """Extract domain from URL."""
        from urllib.parse import urlparse
        try:
            parsed = urlparse(url)
            return parsed.netloc.lower()
        except Exception:
            return None
