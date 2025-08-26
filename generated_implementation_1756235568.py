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
            
            # Process date and time
            starts_at_utc = self._parse_datetime(date_str, time_str)
            if not starts_at_utc:
                continue  # Skip events with unparseable dates
            
            # Extract price information
            price_node = event_node.css_first(".event-card__price")
            price_text = price_node.text(strip=True) if price_node else ""
            price_min, price_max = self._parse_price(price_text)
            
            # Extract ticket URL
            ticket_link = event_node.css_first("a.event-card__button")
            ticket_url = ticket_link.attributes.get("href") if ticket_link else None
            
            # Extract age restriction if available
            age_restriction = self._extract_age_restriction(event_node)
            
            # Extract event ID if available
            event_id_node = event_node.css_first("[data-event-id]")
            external_id = event_id_node.attributes.get("data-event-id") if event_id_node else None
            
            # Create event result
            events.append(ExtractResult(
                site_slug=self.site_slug,
                venue_name="Music Farm",
                title=title,
                artist_name=artist_name,
                starts_at_utc=starts_at_utc,
                ends_at_utc=None,  # End time not provided
                tz_name=self.tz_name,
                doors_time_utc=None,  # Doors time not consistently provided
                price_min=price_min,
                price_max=price_max,
                currency="USD",
                ticket_url=ticket_url,
                age_restriction=age_restriction,
                is_cancelled=False,  # Cancelled status not explicitly shown
                source_url=self.source_url,
                external_id=external_id,
                raw_data={"html_snippet": str(event_node.html)} if event_node else None,
            ))
        
        return events
    
    def _parse_datetime(self, date_str: str, time_str: str) -> Optional[str]:
        """Parse date and time strings into UTC ISO format."""
        try:
            # Clean up the date string (format typically: "MON, JAN 1")
            date_str = date_str.strip()
            
            # Extract the time part (format typically: "Doors: 7:00 PM / Show: 8:00 PM")
            show_time = None
            if "Show:" in time_str:
                show_time = time_str.split("Show:")[1].strip().split("/")[0].strip()
            elif "Doors:" in time_str:
                # If only doors time is available, use that
                show_time = time_str.split("Doors:")[1].strip().split("/")[0].strip()
            else:
                show_time = time_str.strip()
            
            if not show_time:
                return None
                
            # Get current year (Music Farm doesn't include year in their listings)
            current_year = datetime.now().year
            
            # Combine date parts
            full_date_str = f"{date_str}, {current_year} {show_time}"
            
            # Parse the datetime
            dt = datetime.strptime(full_date_str, "%a, %b %d, %Y %I:%M %p")
            
            # Handle year rollover for future dates
            if dt.month < datetime.now().month and dt.day < datetime.now().day:
                dt = dt.replace(year=current_year + 1)
                
            # Convert to UTC
            local_tz = ZoneInfo(self.tz_name)
            dt_local = dt.replace(tzinfo=local_tz)
            dt_utc = dt_local.astimezone(ZoneInfo("UTC"))
            
            return dt_utc.isoformat().replace("+00:00", "Z")
        except Exception:
            return None
    
    def _parse_price(self, price_text: str) -> tuple[Optional[float], Optional[float]]:
        """Parse price information from text."""
        if not price_text or price_text.lower() == "free":
            return 0.0, 0.0
            
        # Remove non-price text
        price_text = price_text.replace("Tickets:", "").strip()
        
        # Check for price range (e.g., "$20-$25")
        if "-" in price_text or "–" in price_text:
            parts = re.split(r"[-–]", price_text)
            try:
                min_price = float(re.sub(r"[^\d.]", "", parts[0]))
                max_price = float(re.sub(r"[^\d.]", "", parts[1]))
                return min_price, max_price
            except (ValueError, IndexError):
                pass
        
        # Check for single price
        try:
            price = float(re.sub(r"[^\d.]", "", price_text))
            return price, price
        except ValueError:
            return None, None
    
    def _extract_age_restriction(self, event_node) -> Optional[str]:
        """Extract age restriction information if available."""
        # Look for age restriction in various places
        for selector in [".event-card__age", ".event-card__details"]:
            node = event_node.css_first(selector)
            if node:
                text = node.text(strip=True)
                
                # Common age restriction patterns
                age_patterns = [
                    r"(\d+)\+",
                    r"(\d+) and over",
                    r"(\d+) & over",
                    r"Ages (\d+)\+",
                    r"All Ages"
                ]
                
                for pattern in age_patterns:
                    match = re.search(pattern, text, re.IGNORECASE)
                    if match:
                        if "all ages" in text.lower():
                            return "All Ages"
                        return f"{match.group(1)}+"
        
        return None