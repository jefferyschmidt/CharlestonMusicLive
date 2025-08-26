# collector/extractors/music_farm.py
from datetime import datetime
from typing import List, Optional
from selectolax.parser import HTMLParser
from zoneinfo import ZoneInfo
import re

from .base import Extractor, ExtractResult

class MusicFarmExtractor(Extractor):
    """Extractor for Music Farm venue events."""
    
    def parse(self, html: str) -> List[ExtractResult]:
        """Parse HTML from Music Farm website and extract event information."""
        tree = HTMLParser(html)
        events: List[ExtractResult] = []
        
        # Music Farm events are in article.event-card elements
        for event_node in tree.css("article.event-card"):
            # Extract event details
            title_node = event_node.css_first(".event-card__title")
            title = title_node.text(strip=True) if title_node else ""
            
            # Artist name is typically the same as title for this venue
            artist_name = title
            
            # Extract date and time
            date_node = event_node.css_first(".event-card__date")
            date_str = date_node.text(strip=True) if date_node else ""
            
            time_node = event_node.css_first(".event-card__time")
            time_str = time_node.text(strip=True) if time_node else ""
            
            # Parse date and time
            starts_at_utc = self._parse_datetime(date_str, time_str)
            
            # Extract price information
            price_node = event_node.css_first(".event-card__price")
            price_text = price_node.text(strip=True) if price_node else ""
            price_min, price_max = self._parse_price(price_text)
            
            # Extract ticket URL
            ticket_link = event_node.css_first("a.event-card__link")
            ticket_url = ticket_link.attributes.get("href") if ticket_link else None
            
            # Extract age restriction if available
            age_node = event_node.css_first(".event-card__age")
            age_restriction = age_node.text(strip=True) if age_node else None
            
            # Extract external ID if available (usually in the URL or as a data attribute)
            external_id = None
            if ticket_url:
                # Try to extract ID from URL
                id_match = re.search(r'/events/([^/]+)', ticket_url)
                if id_match:
                    external_id = id_match.group(1)
            
            # Create event result
            events.append(ExtractResult(
                site_slug=self.site_slug,
                venue_name="Music Farm",
                title=title,
                artist_name=artist_name,
                starts_at_utc=starts_at_utc,
                ends_at_utc=None,  # End time not provided
                tz_name=self.tz_name,
                doors_time_utc=None,  # Doors time not provided
                price_min=price_min,
                price_max=price_max,
                currency="USD",
                ticket_url=ticket_url,
                age_restriction=age_restriction,
                is_cancelled=False,  # Assuming no cancellation info
                source_url=self.source_url,
                external_id=external_id,
                raw_data={"date_str": date_str, "time_str": time_str} if date_str or time_str else None,
            ))
        
        return events
    
    def _parse_datetime(self, date_str: str, time_str: str) -> str:
        """Parse date and time strings into UTC ISO format."""
        try:
            # Clean up the date string (e.g., "FRI, JAN 12" -> "JAN 12 2023")
            date_parts = date_str.strip().split(',', 1)
            if len(date_parts) > 1:
                date_str = date_parts[1].strip()
            
            # Add current year if not present
            if not any(str(year) in date_str for year in range(2020, 2030)):
                date_str = f"{date_str} {datetime.now().year}"
            
            # Parse time (e.g., "Doors: 8:00 PM" -> "8:00 PM")
            time_match = re.search(r'(\d+:\d+\s*[APMapm]{2})', time_str)
            if time_match:
                time_str = time_match.group(1)
            else:
                # Default to 8:00 PM if time not found
                time_str = "8:00 PM"
            
            # Combine date and time
            dt_str = f"{date_str} {time_str}"
            
            # Parse with multiple format attempts
            for fmt in [
                "%b %d %Y %I:%M %p",
                "%B %d %Y %I:%M %p",
                "%b %d %Y %I:%M%p",
                "%B %d %Y %I:%M%p"
            ]:
                try:
                    dt_local = datetime.strptime(dt_str, fmt)
                    dt_local = dt_local.replace(tzinfo=ZoneInfo(self.tz_name))
                    return dt_local.astimezone(datetime.timezone.utc).isoformat().replace("+00:00", "Z")
                except ValueError:
                    continue
            
            # If all formats fail, raise exception
            raise ValueError(f"Could not parse date/time: {dt_str}")
            
        except Exception as e:
            # Fallback to current date/time if parsing fails
            dt_local = datetime.now().replace(tzinfo=ZoneInfo(self.tz_name))
            return dt_local.astimezone(datetime.timezone.utc).isoformat().replace("+00:00", "Z")
    
    def _parse_price(self, price_text: str) -> tuple[Optional[float], Optional[float]]:
        """Parse price information from text."""
        if not price_text or price_text.lower() in ["free", "tbd", "sold out"]:
            return None, None
        
        # Remove currency symbols and clean up
        price_text = price_text.replace("$", "").strip()
        
        # Check for price range (e.g., "15-20" or "15 - 20")
        if "-" in price_text or "–" in price_text:
            parts = re.split(r'[-–]', price_text)
            try:
                price_min = float(parts[0].strip())
                price_max = float(parts[1].strip())
                return price_min, price_max
            except (ValueError, IndexError):
                pass
        
        # Single price
        try:
            price = float(price_text)
            return price, price
        except ValueError:
            return None, None