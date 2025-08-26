# collector/extractors/music_farm.py
from datetime import datetime
from typing import List, Optional, Dict, Any
import re
from selectolax.parser import HTMLParser
from zoneinfo import ZoneInfo

from .base import Extractor, ExtractResult

class MusicFarmExtractor(Extractor):
    """Extractor for Music Farm venue events."""

    def parse(self, html: str) -> List[ExtractResult]:
        """Parse HTML from Music Farm website and extract event information."""
        tree = HTMLParser(html)
        events: List[ExtractResult] = []

        # Music Farm lists events in article elements with class "event-card"
        for event_node in tree.css("article.event-card"):
            # Extract event details
            title_node = event_node.css_first(".title")
            title = title_node.text(strip=True) if title_node else ""
            
            # Artist name is typically the same as title for this venue
            artist_name = title
            
            # Extract date and time
            date_node = event_node.css_first(".date")
            date_str = date_node.text(strip=True) if date_node else ""
            
            time_node = event_node.css_first(".time")
            time_str = time_node.text(strip=True) if time_node else ""
            
            # Extract ticket information
            ticket_node = event_node.css_first("a.btn-tickets")
            ticket_url = ticket_node.attributes.get("href") if ticket_node else None
            
            # Extract price information
            price_node = event_node.css_first(".price")
            price_text = price_node.text(strip=True) if price_node else ""
            
            # Extract age restriction
            age_node = event_node.css_first(".age-restriction")
            age_restriction = age_node.text(strip=True) if age_node else None
            
            # Process date and time
            starts_at_utc = self._parse_datetime(date_str, time_str)
            
            # Process price information
            price_min, price_max = self._parse_price(price_text)
            
            # Extract any additional information for raw data
            description_node = event_node.css_first(".description")
            description = description_node.text(strip=True) if description_node else None
            
            # Extract external ID if available
            external_id = event_node.attributes.get("id") or None
            
            # Create event result
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
            
            # Extract date components
            date_match = re.search(r'(\w+),\s+(\w+)\s+(\d+),\s+(\d{4})', date_str)
            if date_match:
                _, month, day, year = date_match.groups()
            else:
                # Fallback parsing if the format is different
                parts = date_str.replace(',', '').split()
                if len(parts) >= 3:
                    month, day, year = parts[1], parts[2], parts[3]
                else:
                    raise ValueError(f"Unable to parse date: {date_str}")
            
            # Extract time
            time_match = re.search(r'(\d+):(\d+)\s*(PM|AM)', time_str, re.IGNORECASE)
            if time_match:
                hour, minute, ampm = time_match.groups()
                hour = int(hour)
                if ampm.upper() == 'PM' and hour < 12:
                    hour += 12
                elif ampm.upper() == 'AM' and hour == 12:
                    hour = 0
                time_formatted = f"{hour:02d}:{minute}"
            else:
                # Default to 8 PM if time not found
                time_formatted = "20:00"
            
            # Convert month name to number
            month_map = {
                'jan': 1, 'feb': 2, 'mar': 3, 'apr': 4, 'may': 5, 'jun': 6,
                'jul': 7, 'aug': 8, 'sep': 9, 'oct': 10, 'nov': 11, 'dec': 12
            }
            month_num = month_map.get(month.lower()[:3], 1)
            
            # Create datetime object
            dt_str = f"{year}-{month_num:02d}-{int(day):02d}T{time_formatted}:00"
            dt_local = datetime.fromisoformat(dt_str).replace(tzinfo=ZoneInfo(self.tz_name))
            
            # Convert to UTC
            dt_utc = dt_local.astimezone(datetime.UTC)
            return dt_utc.isoformat().replace("+00:00", "Z")
        except Exception as e:
            # Fallback to a default time if parsing fails
            return datetime.now(datetime.UTC).isoformat().replace("+00:00", "Z")

    def _parse_price(self, price_text: str) -> tuple[Optional[float], Optional[float]]:
        """Parse price information from text."""
        if not price_text:
            return None, None
        
        # Remove currency symbols and extra text
        price_text = price_text.replace("$", "").strip()
        
        # Check for price range (e.g., "$15-$20" or "$15 – $20")
        if "-" in price_text or "–" in price_text:
            parts = re.split(r'[-–]', price_text)
            try:
                min_price = float(parts[0].strip())
                max_price = float(parts[1].strip())
                return min_price, max_price
            except (ValueError, IndexError):
                pass
        
        # Check for single price
        try:
            price = float(re.search(r'\d+(\.\d+)?', price_text).group())
            return price, price
        except (ValueError, AttributeError):
            return None, None