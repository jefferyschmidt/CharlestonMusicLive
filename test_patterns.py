#!/usr/bin/env python3
"""Test what patterns are found in the HTML."""

import asyncio
import aiohttp

async def test_patterns():
    """Test what patterns are found in the HTML."""
    
    url = 'https://www.musicfarm.com/calendar'
    
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(url) as response:
                if response.status == 200:
                    html = await response.text()
                    html_lower = html.lower()
                    
                    print(f"🔍 Testing patterns in HTML from {url}")
                    print(f"HTML length: {len(html)} characters")
                    print()
                    
                    # Check sample venue patterns
                    print("Sample venue patterns:")
                    print(f"  'sample' in HTML: {'sample' in html_lower}")
                    print(f"  'test' in HTML: {'test' in html_lower}")
                    print(f"  'fixture' in HTML: {'fixture' in html_lower}")
                    print()
                    
                    # Check Music Farm patterns
                    print("Music Farm patterns:")
                    print(f"  'musicfarm' in HTML: {'musicfarm' in html_lower}")
                    print(f"  'music farm' in HTML: {'music farm' in html_lower}")
                    print()
                    
                    # Check for any other patterns
                    print("Other patterns found:")
                    if 'sample' in html_lower:
                        print("  Found 'sample' - this is why it matches sample_venue!")
                    if 'test' in html_lower:
                        print("  Found 'test' - this is why it matches sample_venue!")
                    if 'fixture' in html_lower:
                        print("  Found 'fixture' - this is why it matches sample_venue!")
                    
                else:
                    print(f"Failed to fetch {url}: HTTP {response.status}")
                    
    except Exception as e:
        print(f"Error testing patterns: {e}")

if __name__ == "__main__":
    asyncio.run(test_patterns())
