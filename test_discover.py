#!/usr/bin/env python3
"""Test script for the discover command to see what's happening."""

import asyncio
import json
from collector.intelligent_crawler import discover_and_crawl_sources

async def main():
    print("🧪 Testing discover command...")
    print("=" * 50)
    
    try:
        result = await discover_and_crawl_sources(
            site_slug="charleston",
            city="Charleston", 
            state="SC",
            max_sources=3
        )
        
        print("✅ Discover command completed successfully!")
        print("\n📊 Results:")
        
        # Access discovery results
        discovery = result['discovery']
        print(f"Discovery sources found: {len(discovery.sources)}")
        print(f"Discovery method: {discovery.discovery_method}")
        print(f"Search terms used: {', '.join(discovery.search_terms)}")
        print(f"Discovery execution time: {discovery.execution_time:.1f}s")
        
        # Access crawl results
        crawl = result['crawl']
        print(f"Crawl session completed: {crawl.sources_crawled} sources crawled")
        print(f"Total events found: {crawl.total_events_found}")
        print(f"Successful crawls: {crawl.successful_crawls}")
        print(f"Failed crawls: {crawl.failed_crawls}")
        
        print("\n🔍 Discovery Sources:")
        for source in discovery.sources[:5]:
            print(f"  - {source.name}: {source.url}")
            print(f"    Type: {source.source_type}, Confidence: {source.confidence_score:.2f}")
            if source.venue_name:
                print(f"    Venue: {source.venue_name}")
        
        print("\n📈 Crawl Statistics:")
        stats = result['statistics']
        print(f"  - Duration: {stats.get('duration_seconds', 0):.1f}s")
        print(f"  - Success rate: {stats.get('success_rate', 0):.1%}")
        print(f"  - Events per source: {stats.get('events_per_source', 0):.1f}")
        
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(main())
