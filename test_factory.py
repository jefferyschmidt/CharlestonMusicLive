#!/usr/bin/env python3
"""Test the ExtractorFactory directly."""

import asyncio
import aiohttp
from collector.extractors.factory import ExtractorFactory

async def test_factory():
    """Test the ExtractorFactory with Music Farm."""
    
    url = 'https://www.musicfarm.com/calendar'
    
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(url) as response:
                if response.status == 200:
                    html = await response.text()
                    print(f"Fetched {len(html)} characters from {url}")
                    
                    # Test the factory
                    factory = ExtractorFactory()
                    
                    # Test pattern matching
                    url_lower = url.lower()
                    html_lower = html.lower()
                    
                    print(f"\n🔍 Testing pattern matching:")
                    print(f"URL: {url}")
                    print(f"'musicfarm' in URL: {'musicfarm' in url_lower}")
                    print(f"'music farm' in URL: {'music farm' in url_lower}")
                    
                    # Test the factory analysis
                    print(f"\n🎯 Testing factory analysis:")
                    extractor_match = factory.analyze_source(
                        url, html, {
                            'venue_name': 'Music Farm',
                            'source_type': 'venue',
                            'calendar_detected': True,
                            'requires_browser': False
                        }
                    )
                    
                    print(f"Extractor match: {extractor_match}")
                    print(f"Extractor class: {extractor_match.extractor_class.__name__}")
                    print(f"Confidence: {extractor_match.confidence_score}")
                    print(f"Reasoning: {extractor_match.reasoning}")
                    
                    # Test creating the extractor
                    print(f"\n🔧 Testing extractor creation:")
                    extractor = factory.create_extractor(extractor_match, 'charleston', url)
                    print(f"Created extractor: {extractor.__class__.__name__}")
                    
                    # Test parsing
                    print(f"\n📝 Testing parsing:")
                    events = extractor.parse(html)
                    print(f"Found {len(events)} events")
                    
                else:
                    print(f"Failed to fetch {url}: HTTP {response.status}")
                    
    except Exception as e:
        print(f"Error testing factory: {e}")

if __name__ == "__main__":
    asyncio.run(test_factory())
