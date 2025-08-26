#!/usr/bin/env python3
"""Test crawling Music Farm and storing events to database."""

import asyncio
import aiohttp
from collector.extractors.music_farm import MusicFarmExtractor
from collector.intelligent_crawler import IntelligentCrawler
from collector.discovery.source_discoverer import DiscoveredSource

async def test_music_farm_crawl():
    """Test crawling Music Farm and storing events."""
    
    # Create a test source for Music Farm
    music_farm_source = DiscoveredSource(
        name="Music Farm",
        url="https://www.musicfarm.com/calendar",
        source_type="venue",  # Use string instead of enum
        confidence_score=0.9,
        venue_name="Music Farm",
        address="32 Ann St, Charleston, SC 29403",
        phone=None,
        description="Live music venue in Charleston",
        event_count=55,
        calendar_detected=True,
        requires_browser=False,
        rate_limit_rps=1.0,
        priority_score=0.9
    )
    
    # Create crawler and initialize it properly
    async with IntelligentCrawler('charleston', 'Charleston', 'SC') as crawler:
        # Test crawling just Music Farm
        print("🎯 Testing Music Farm crawl...")
        
        try:
            # Crawl the single source
            crawl_result = await crawler._crawl_single_source(music_farm_source)
            
            print(f"Crawl result: {crawl_result}")
            print(f"Success: {crawl_result.success}")
            print(f"Events found: {crawl_result.events_found}")
            print(f"Events extracted: {crawl_result.events_extracted}")
            
            if crawl_result.success and crawl_result.events_extracted > 0:
                print("✅ Successfully extracted events from Music Farm!")
                
                # Try to store the events
                print("💾 Attempting to store events to database...")
                # We need to get the events from the extractor since they're not stored in crawl_result
                extractor = MusicFarmExtractor('charleston', music_farm_source.url)
                async with aiohttp.ClientSession() as session:
                    async with session.get(music_farm_source.url) as response:
                        html = await response.text()
                        events = extractor.parse(html)
                        stored_events = await crawler._store_events_from_source(music_farm_source, events)
                        print(f"Stored {len(stored_events)} events to database")
                
            else:
                print("❌ Failed to extract events from Music Farm")
                
        except Exception as e:
            print(f"Error during crawl: {e}")

if __name__ == "__main__":
    asyncio.run(test_music_farm_crawl())
