"""
The Music Farm Charleston Extractor

Extracts live music events from The Music Farm Charleston website.
"""
from typing import List, Optional, Dict, Any
from datetime import datetime, timezone
import re
from selectolax.parser import HTMLParser
from .base import Extractor, ExtractResult


class MusicFarmExtractor(Extractor):
    """Extractor for The Music Farm Charleston events."""
    
    def __init__(self, site_slug: str = "charleston", source_url: str = ""):
        super().__init__(site_slug, source_url)
        self.venue_name = "The Music Farm"
        self.tz_name = "America/New_York"
    
    def parse(self, html_content: str) -> List[ExtractResult]:
        """Parse HTML content and extract event information."""
        parser = HTMLParser(html_content)
        events = []
        
        # Look for event containers - this will need to be adjusted based on actual HTML structure
        # Common patterns for event listings
        event_selectors = [
            ".event-item",
            ".event",
            ".show-item", 
            ".concert-item",
            "[class*='event']",
            "[class*='show']",
            "[class*='concert']"
        ]
        
        # Try different selectors to find events
        event_elements = []
        for selector in event_selectors:
            elements = parser.css(selector)
            if elements:
                event_elements = elements
                break
        
        # If no specific selectors work, look for common patterns
        if not event_elements:
            # Look for elements with dates or event-like content
            date_elements = parser.css("[class*='date'], [class*='time'], [class*='when']")
            if date_elements:
                # Use parent containers that might contain events
                event_elements = [elem.parent for elem in date_elements if elem.parent]
        
        for element in event_elements:
            try:
                event = self._extract_single_event(element)
                if event:
                    events.append(event)
            except Exception as e:
                # Log error but continue processing other events
                print(f"Error extracting event: {e}")
                continue
        
        return events
    
    def _extract_single_event(self, element) -> Optional[ExtractResult]:
        """Extract a single event from an HTML element."""
        # Extract title/artist
        title = self._extract_text(element, [
            ".event-title", ".title", ".name", "h1", "h2", "h3", "[class*='title']"
        ])
        
        if not title:
            return None
        
        # Extract artist name (might be separate or part of title)
        artist_name = self._extract_text(element, [
            ".artist", ".performer", ".band", "[class*='artist']", "[class*='performer']"
        ])
        
        # If no separate artist, try to parse from title
        if not artist_name and " - " in title:
            parts = title.split(" - ", 1)
            if len(parts) == 2:
                artist_name = parts[0].strip()
                title = parts[1].strip()
        
        # Extract date/time
        date_text = self._extract_text(element, [
            ".date", ".time", ".when", "[class*='date']", "[class*='time']"
        ])
        
        if not date_text:
            return None
        
        # Parse date/time
        starts_at_utc, ends_at_utc = self._parse_datetime(date_text)
        if not starts_at_utc:
            return None
        
        # Extract price
        price_text = self._extract_text(element, [
            ".price", ".cost", ".ticket-price", "[class*='price']"
        ])
        price_min, price_max = self._parse_price(price_text)
        
        # Extract ticket URL
        ticket_url = self._extract_href(element, [
            ".ticket-link", ".buy-tickets", "a[href*='ticket']", "a[href*='buy']"
        ])
        
        # Extract age restriction
        age_text = self._extract_text(element, [
            ".age", ".age-restriction", "[class*='age']"
        ])
        age_restriction = self._parse_age_restriction(age_text)
        
        # Extract external ID (from URL or data attribute)
        external_id = self._extract_external_id(element)
        
        # Extract raw data for debugging
        raw_data = {
            "title": title,
            "artist_name": artist_name,
            "date_text": date_text,
            "price_text": price_text,
            "age_text": age_text,
            "element_html": element.html[:500]  # First 500 chars for debugging
        }
        
        return ExtractResult(
            site_slug=self.site_slug,
            venue_name=self.venue_name,
            title=title,
            artist_name=artist_name,
            starts_at_utc=starts_at_utc,
            ends_at_utc=ends_at_utc,
            tz_name=self.tz_name,
            doors_time_utc=None,  # Not typically available
            price_min=price_min,
            price_max=price_max,
            currency="USD",
            ticket_url=ticket_url,
            age_restriction=age_restriction,
            is_cancelled=False,  # Assume not cancelled unless indicated
            source_url=self.source_url,
            external_id=external_id,
            raw_data=raw_data
        )
    
    def _extract_text(self, element, selectors: List[str]) -> Optional[str]:
        """Extract text content using multiple selectors."""
        for selector in selectors:
            found = element.css_first(selector)
            if found:
                text = found.text().strip()
                if text:
                    return text
        return None
    
    def _extract_href(self, element, selectors: List[str]) -> Optional[str]:
        """Extract href attribute using multiple selectors."""
        for selector in selectors:
            found = element.css_first(selector)
            if found and found.attributes.get('href'):
                return found.attributes['href']
        return None
    
    def _parse_datetime(self, date_text: str) -> tuple[Optional[str], Optional[str]]:
        """Parse date/time text into UTC datetime strings."""
        if not date_text:
            return None, None
        
        # Common date formats for The Music Farm
        date_patterns = [
            # "Friday, January 15, 2025 at 8:00 PM"
            r'(\w+),\s+(\w+)\s+(\d{1,2}),?\s+(\d{4})\s+(?:at\s+)?(\d{1,2}):(\d{2})\s*(AM|PM)',
            # "Jan 15, 2025 8:00 PM"
            r'(\w{3})\s+(\d{1,2}),?\s+(\d{4})\s+(\d{1,2}):(\d{2})\s*(AM|PM)',
            # "2025-01-15 20:00"
            r'(\d{4})-(\d{1,2})-(\d{1,2})\s+(\d{1,2}):(\d{2})',
            # "01/15/2025 8:00 PM"
            r'(\d{1,2})/(\d{1,2})/(\d{4})\s+(\d{1,2}):(\d{2})\s*(AM|PM)',
        ]
        
        for pattern in date_patterns:
            match = re.search(pattern, date_text, re.IGNORECASE)
            if match:
                try:
                    if len(match.groups()) == 7:  # First pattern
                        day_name, month_name, day, year, hour, minute, ampm = match.groups()
                        month = self._month_name_to_number(month_name)
                    elif len(match.groups()) == 6:  # Second pattern
                        month_abbr, day, year, hour, minute, ampm = match.groups()
                        month = self._month_abbr_to_number(month_abbr)
                    elif len(match.groups()) == 5:  # Third pattern (24-hour)
                        year, month, day, hour, minute = match.groups()
                        ampm = None
                    elif len(match.groups()) == 6:  # Fourth pattern
                        month, day, year, hour, minute, ampm = match.groups()
                    else:
                        continue
                    
                    # Convert to integers
                    year = int(year)
                    month = int(month)
                    day = int(day)
                    hour = int(hour)
                    minute = int(minute)
                    
                    # Handle AM/PM
                    if ampm and ampm.upper() == 'PM' and hour != 12:
                        hour += 12
                    elif ampm and ampm.upper() == 'AM' and hour == 12:
                        hour = 0
                    
                    # Create datetime object (assume Eastern time)
                    dt = datetime(year, month, day, hour, minute, tzinfo=timezone.utc)
                    
                    # Convert to UTC (Eastern is UTC-5 or UTC-4 depending on DST)
                    # For now, assume EST (UTC-5) - this could be made more sophisticated
                    dt = dt.replace(tzinfo=timezone.utc)
                    
                    # Format as ISO string
                    starts_at_utc = dt.isoformat()
                    
                    # Assume 2-3 hour duration for most shows
                    ends_at_utc = (dt.replace(hour=(dt.hour + 2) % 24)).isoformat()
                    
                    return starts_at_utc, ends_at_utc
                    
                except (ValueError, TypeError):
                    continue
        
        return None, None
    
    def _month_name_to_number(self, month_name: str) -> int:
        """Convert month name to number."""
        months = {
            'january': 1, 'february': 2, 'march': 3, 'april': 4,
            'may': 5, 'june': 6, 'july': 7, 'august': 8,
            'september': 9, 'october': 10, 'november': 11, 'december': 12
        }
        return months.get(month_name.lower(), 1)
    
    def _month_abbr_to_number(self, month_abbr: str) -> int:
        """Convert month abbreviation to number."""
        months = {
            'jan': 1, 'feb': 2, 'mar': 3, 'apr': 4,
            'may': 5, 'jun': 6, 'jul': 7, 'aug': 8,
            'sep': 9, 'oct': 10, 'nov': 11, 'dec': 12
        }
        return months.get(month_abbr.lower(), 1)
    
    def _parse_price(self, price_text: str) -> tuple[Optional[float], Optional[float]]:
        """Parse price text into min/max values."""
        if not price_text:
            return None, None
        
        # Look for price ranges first (more specific)
        range_match = re.search(r'\$?(\d+(?:\.\d{2})?)\s*[-–]\s*\$?(\d+(?:\.\d{2})?)', price_text)
        if range_match:
            min_price = float(range_match.group(1))
            max_price = float(range_match.group(2))
            return min_price, max_price
        
        # Extract single price if no range found
        price_match = re.search(r'\$?(\d+(?:\.\d{2})?)', price_text)
        if price_match:
            price = float(price_match.group(1))
            return price, price  # Same min/max for single price
        
        return None, None
    
    def _parse_age_restriction(self, age_text: str) -> Optional[str]:
        """Parse age restriction text."""
        if not age_text:
            return None
        
        age_text = age_text.lower()
        if 'all ages' in age_text or 'family' in age_text:
            return "All Ages"
        elif '21+' in age_text or '21 and up' in age_text:
            return "21+"
        elif '18+' in age_text or '18 and up' in age_text:
            return "18+"
        
        return None
    
    def _extract_external_id(self, element) -> Optional[str]:
        """Extract external ID from element."""
        # Look for data attributes
        for attr in ['data-event-id', 'data-id', 'id']:
            value = element.attributes.get(attr)
            if value:
                return value
        
        # Look for URL-based ID
        href = element.attributes.get('href')
        if href:
            # Extract ID from URL if present
            id_match = re.search(r'/(\d+)(?:/|$)', href)
            if id_match:
                return id_match.group(1)
        
        return None
