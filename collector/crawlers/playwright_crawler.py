"""
Playwright crawler for JavaScript-rendered content.
"""

import asyncio
from typing import Optional, Dict, Any
from playwright.async_api import async_playwright, Browser, Page
from .base import BaseCrawler, CrawlResult


class PlaywrightCrawler(BaseCrawler):
    """Playwright-based crawler for JavaScript-rendered content."""
    
    def __init__(self, source_id: int, url: str, politeness_delay_ms: int = 1000,
                 respect_robots_txt: bool = True, headers: Optional[Dict[str, str]] = None,
                 wait_for_selector: Optional[str] = None, wait_timeout: int = 10000,
                 viewport_size: Optional[Dict[str, int]] = None):
        super().__init__(source_id, url, politeness_delay_ms, respect_robots_txt, headers)
        self.wait_for_selector = wait_for_selector
        self.wait_timeout = wait_timeout
        self.viewport_size = viewport_size or {"width": 1280, "height": 720}
    
    async def crawl(self) -> CrawlResult:
        """Crawl the URL using Playwright and return the result."""
        start_time = asyncio.get_event_loop().time()
        
        try:
            # Respect politeness delay
            await self._respect_politeness()
            
            async with async_playwright() as p:
                # Launch browser
                browser = await p.chromium.launch(
                    headless=True,
                    args=[
                        '--no-sandbox',
                        '--disable-setuid-sandbox',
                        '--disable-dev-shm-usage',
                        '--disable-accelerated-2d-canvas',
                        '--no-first-run',
                        '--no-zygote',
                        '--disable-gpu'
                    ]
                )
                
                try:
                    # Create context and page
                    context = await browser.new_context(
                        viewport=self.viewport_size,
                        user_agent=self.headers.get('User-Agent', 'MusicLive Crawler/0.1')
                    )
                    
                    page = await context.new_page()
                    
                    # Set extra headers
                    for key, value in self.headers.items():
                        if key.lower() != 'user-agent':  # Already set in context
                            await page.set_extra_http_headers({key: value})
                    
                    # Navigate to URL
                    response = await page.goto(self.url, wait_until='networkidle', timeout=30000)
                    
                    # Wait for specific selector if provided
                    if self.wait_for_selector:
                        try:
                            await page.wait_for_selector(self.wait_for_selector, timeout=self.wait_timeout)
                        except Exception:
                            # Continue even if selector doesn't appear
                            pass
                    
                    # Wait a bit more for dynamic content
                    await asyncio.sleep(2)
                    
                    # Get the rendered content
                    content = await page.content()
                    
                    # Get the final HTML after JavaScript execution
                    rendered_content = await page.evaluate("() => document.documentElement.outerHTML")
                    
                    end_time = asyncio.get_event_loop().time()
                    crawl_time_ms = int((end_time - start_time) * 1000)
                    
                    return CrawlResult(
                        source_id=self.source_id,
                        url=self.url,
                        content=content,
                        status_code=response.status if response else 200,
                        headers=dict(response.headers) if response else {},
                        crawl_time_ms=crawl_time_ms,
                        content_type='text/html',
                        rendered_content=rendered_content,
                        metadata={
                            'browser': 'chromium',
                            'viewport': self.viewport_size,
                            'wait_for_selector': self.wait_for_selector,
                            'wait_timeout': self.wait_timeout
                        }
                    )
                    
                finally:
                    await browser.close()
                    
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
