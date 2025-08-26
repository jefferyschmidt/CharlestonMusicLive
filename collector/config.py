"""
Crawler Configuration

Centralized configuration for crawler behavior, rate limiting, and politeness settings.
"""
import os
from typing import Dict, Any

# Rate limiting and politeness settings
CRAWLER_CONFIG = {
    # Request delays (in seconds)
    'min_delay_between_requests': 1.0,
    'max_delay_between_requests': 3.0,
    'delay_multiplier_on_error': 2.0,
    
    # Concurrent requests
    'max_concurrent_requests': 3,
    'max_concurrent_artists': 5,
    
    # Timeouts
    'request_timeout': 30,
    'page_load_timeout': 60,
    
    # Retry settings
    'max_retries': 3,
    'retry_delay': 5,
    
    # Politeness settings
    'respect_robots_txt': True,
    'user_agent': 'Mozilla/5.0 (compatible; MusicLiveBot/1.0; +https://musiclive.com/bot)',
    'max_requests_per_domain_per_hour': 100,
    
    # Content limits
    'max_page_size_mb': 10,
    'max_events_per_venue': 200,
    
    # Artist research settings
    'artist_research_enabled': True,
    'max_artist_research_per_crawl': 50,
    'artist_research_delay': 1.0,
    
    # Learning and adaptation
    'enable_pattern_learning': True,
    'max_learned_patterns': 1000,
    'pattern_confidence_threshold': 0.6
}

# Venue-specific overrides
VENUE_OVERRIDES = {
    'musicfarm.com': {
        'min_delay_between_requests': 2.0,
        'max_events_per_venue': 100
    },
    'charlestonmusichall.com': {
        'min_delay_between_requests': 2.0,
        'max_events_per_venue': 150
    }
}

def get_config_for_domain(domain: str) -> Dict[str, Any]:
    """Get configuration for a specific domain with overrides."""
    config = CRAWLER_CONFIG.copy()
    
    if domain in VENUE_OVERRIDES:
        config.update(VENUE_OVERRIDES[domain])
    
    return config

def get_global_config() -> Dict[str, Any]:
    """Get global crawler configuration."""
    return CRAWLER_CONFIG.copy()
