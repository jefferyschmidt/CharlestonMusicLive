"""
Factory for creating crawlers based on source configuration.
"""

from typing import Optional, Dict, Any
from .base import BaseCrawler, CrawlerType
from .http_crawler import HttpCrawler
from .playwright_crawler import PlaywrightCrawler


class CrawlerFactory:
    """Factory for creating crawlers based on configuration."""
    
    @staticmethod
    def create_crawler(
        source_id: int, 
        url: str, 
        crawler_type: CrawlerType, 
        politeness_delay_ms: int = 1000, 
        respect_robots_txt: bool = True,
        headers: Optional[Dict[str, str]] = None,
        **kwargs
    ) -> BaseCrawler:
        """Create a crawler instance based on the specified type."""
        
        if crawler_type == CrawlerType.HTTP:
            return HttpCrawler(
                source_id, 
                url, 
                politeness_delay_ms, 
                respect_robots_txt, 
                headers
            )
            
        elif crawler_type == CrawlerType.PLAYWRIGHT:
            return PlaywrightCrawler(
                source_id, 
                url, 
                politeness_delay_ms, 
                respect_robots_txt, 
                headers,
                wait_for_selector=kwargs.get('wait_for_selector'),
                wait_timeout=kwargs.get('wait_timeout', 10000),
                viewport_size=kwargs.get('viewport_size')
            )
            
        elif crawler_type == CrawlerType.API:
            # For now, use HTTP crawler for API endpoints
            # TODO: Implement dedicated API crawler with rate limiting and authentication
            return HttpCrawler(
                source_id, 
                url, 
                politeness_delay_ms, 
                respect_robots_txt, 
                headers
            )
            
        else:
            raise ValueError(f"Unknown crawler type: {crawler_type}")
    
    @staticmethod
    def determine_crawler_type(
        requires_browser: bool = False,
        is_api_endpoint: bool = False,
        has_javascript_content: bool = False
    ) -> CrawlerType:
        """Determine the appropriate crawler type based on source characteristics."""
        
        if is_api_endpoint:
            return CrawlerType.API
        elif requires_browser or has_javascript_content:
            return CrawlerType.PLAYWRIGHT
        else:
            return CrawlerType.HTTP
