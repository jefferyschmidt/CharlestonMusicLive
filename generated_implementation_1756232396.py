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
        tree = HTMLParser(html)
        events: List[ExtractResult] = []

        # Music Farm events are in .eventWrapper elements
        for event_node in tree.css(".eventWrapper"):
            # Extract event details
            title_node = event_node.css_first(".title")
            title = title_node.text(strip=True) if title_node else ""
            
            # Artist name is usually the same as title for this venue
            artist_name = title
            
            # Extract date and time
            date_node = event_node.css_first(".date")
            date_str = date_node.text(strip=True) if date_node else ""
            
            time_node = event_node.css_first(".time")
            time_str = time_node.text(strip=True) if time_node else ""
            
            # Parse date and time
            starts_at_utc = self._parse_datetime(date_str, time_str)
            
            # Extract price information
            price_node = event_node.css_first(".price")
            price_str = price_node.text(strip=True) if price_node else ""
            price_min, price_max = self._parse_price(price_str)
            
            # Extract ticket URL
            ticket_link = event_node.css_first("a.tickets")
            ticket_url = ticket_link.attributes.get("href") if ticket_link else None
            
            # Extract age restriction
            age_node = event_node.css_first(".ageRestriction")
            age_restriction = age_node.text(strip=True) if age_node else None
            
            # Extract event ID if available
            event_id_node = event_node.css_first("[data-event-id]")
            external_id = event_id_node.attributes.get("data-event-id") if event_id_node else None
            
            # Extract additional info for raw data
            description_node = event_node.css_first(".description")
            description = description_node.text(strip=True) if description_node else None
            
            # Create the event result
            events.append(ExtractResult(
                site_slug=self.site_slug,
                venue_name="Music Farm",
                title=title,
                artist_name=artist_name,
                starts_at_utc=starts_at_utc,
                ends_at_utc=None,  # Music Farm doesn't typically list end times
                tz_name=self.tz_name,
                doors_time_utc=None,  # Could be extracted if available
                price_min=price_min,
                price_max=price_max,
                currency="USD",
                ticket_url=ticket_url,
                age_restriction=age_restriction,
                is_cancelled=False,  # Would need specific logic to detect cancellations
                source_url=self.source_url,
                external_id=external_id,
                raw_data={"description": description} if description else None,
            ))

        return events

    def _parse_datetime(self, date_str: str, time_str: str) -> str:
        """Parse date and time strings into UTC ISO format."""
        try:
            # Clean up the date and time strings
            date_str = date_str.strip()
            time_str = time_str.strip()
            
            # Extract doors time if present (e.g., "Doors: 8:00 PM")
            if "doors" in time_str.lower():
                time_str = time_str.lower().replace("doors:", "").strip()
            
            # Parse the date (format: Month Day, Year)
            date_obj = datetime.strptime(date_str, "%B %d, %Y")
            
            # Parse the time (format: HH:MM PM)
            time_obj = datetime.strptime(time_str, "%I:%M %p")
            
            # Combine date and time
            dt_local = datetime.combine(
                date_obj.date(),
                time_obj.time(),
                tzinfo=ZoneInfo(self.tz_name)
            )
            
            # Convert to UTC
            dt_utc = dt_local.astimezone(ZoneInfo("UTC"))
            
            # Format as ISO 8601 with Z suffix
            return dt_utc.isoformat().replace("+00:00", "Z")
        except Exception:
            # Fallback to current time if parsing fails
            return datetime.now(ZoneInfo("UTC")).isoformat().replace("+00:00", "Z")

    def _parse_price(self, price_str: str) -> tuple[Optional[float], Optional[float]]:
        """Parse price string into min and max values."""
        if not price_str:
            return None, None
        
        # Remove currency symbols and whitespace
        price_str = price_str.replace("$", "").strip()
        
        # Check for price range (e.g., "15-20" or "15 - 20")
        if "-" in price_str or "–" in price_str:
            # Normalize dash character
            price_str = price_str.replace("–", "-")
            parts = price_str.split("-")
            try:
                min_price = float(parts[0].strip())
                max_price = float(parts[1].strip())
                return min_price, max_price
            except (ValueError, IndexError):
                pass
        
        # Check for single price
        try:
            price = float(price_str)
            return price, price
        except ValueError:
            pass
        
        # Check for "Free" or similar text
        if "free" in price_str.lower():
            return 0.0, 0.0
        
        return None, None