"""
HTTP crawler for static content using aiohttp.
"""

import asyncio
import aiohttp
from typing import Optional, Dict, Any
from .base import BaseCrawler, CrawlResult


class HttpCrawler(BaseCrawler):
    """Simple HTTP crawler using aiohttp."""
    
    async def crawl(self) -> CrawlResult:
        """Crawl the URL and return the result."""
        start_time = asyncio.get_event_loop().time()
        
        try:
            # Respect politeness delay
            await self._respect_politeness()
            
            async with aiohttp.ClientSession() as session:
                async with session.get(
                    self.url, 
                    headers=self.headers, 
                    timeout=aiohttp.ClientTimeout(total=30)
                ) as response:
                    content = await response.text()
                    end_time = asyncio.get_event_loop().time()
                    crawl_time_ms = int((end_time - start_time) * 1000)
                    
                    return CrawlResult(
                        source_id=self.source_id,
                        url=self.url,
                        content=content,
                        status_code=response.status,
                        headers=dict(response.headers),
                        crawl_time_ms=crawl_time_ms,
                        content_type=response.headers.get('content-type', 'text/html')
                    )
                    
        except Exception as e:
            end_time = asyncio.get_event_loop().time()
            crawl_time_ms = int((end_time - start_time) * 1000)
            
            return CrawlResult(
                source_id=self.source_id,
                url=self.url,
                content="",
                status_code=0,
                headers={},
                crawl_time_ms=crawl_time_ms,
                error=str(e)
            )
