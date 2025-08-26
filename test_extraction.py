#!/usr/bin/env python3
"""Test script for Music Farm extractor."""

import asyncio
import aiohttp
from collector.extractors.music_farm import MusicFarmExtractor
from selectolax.parser import HTMLParser

async def test_music_farm_extraction():
    """Test extracting events from Music Farm."""
    url = 'https://www.musicfarm.com/calendar'
    
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(url) as response:
                if response.status == 200:
                    html = await response.text()
                    print(f"Successfully fetched {len(html)} characters from {url}")
                    
                    # Parse HTML with selectolax
                    tree = HTMLParser(html)
                    
                    # Look for article.event-card elements
                    event_cards = tree.css("article.event-card")
                    print(f"article.event-card: {len(event_cards)} found")
                    
                    # Show the content of the first few event cards
                    print(f"\n📋 Content of first 3 event cards:")
                    for i, card in enumerate(event_cards[:3]):
                        print(f"\n--- Event Card {i+1} ---")
                        print(f"HTML: {card.html[:500]}...")
                        
                        # Check what selectors the extractor is looking for
                        title_node = card.css_first("a[href*='/event/']")
                        date_node = card.css_first(".event-date, .date, .event-time, .time")
                        
                        print(f"Title selector (a[href*='/event/']): {'✅ Found' if title_node else '❌ Not found'}")
                        print(f"Date selector (.event-date, .date, .event-time, .time): {'✅ Found' if date_node else '❌ Not found'}")
                        
                        # Show what we actually found
                        if title_node:
                            print(f"Title text: '{title_node.text(strip=True)}'")
                            print(f"Title HTML: {title_node.html}")
                            # Look for text in child elements
                            for child in title_node.css("*"):
                                if child.text(strip=True):
                                    print(f"Child text: '{child.text(strip=True)}'")
                        if date_node:
                            print(f"Date text: {date_node.text(strip=True)}")
                        
                        # Also check for the event link
                        if title_node:
                            print(f"Event link: {title_node.attributes.get('href')}")
                    
                    # Test the extractor
                    print(f"\n🎯 Testing MusicFarmExtractor:")
                    extractor = MusicFarmExtractor('charleston', url)
                    events = extractor.parse(html)
                    
                    print(f"Found {len(events)} events:")
                    for i, event in enumerate(events[:5]):  # Show first 5
                        print(f"\n{i+1}. {event.title}")
                        print(f"   Artist: {event.artist_name}")
                        print(f"   Date: {event.starts_at_utc}")
                        print(f"   URL: {event.ticket_url}")
                else:
                    print(f"Failed to fetch {url}: HTTP {response.status}")
                    
    except Exception as e:
        print(f"Error testing extraction: {e}")

if __name__ == "__main__":
    asyncio.run(test_music_farm_extraction())
