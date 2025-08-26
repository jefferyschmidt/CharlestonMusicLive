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
            
            # Extract doors time if available
            doors_time = None
            doors_time_utc = None
            if time_str and "Doors:" in time_str:
                doors_match = re.search(r"Doors:\s*(\d+:?\d*\s*[APM]{2})", time_str)
                if doors_match:
                    doors_time = doors_match.group(1).strip()
                    # Extract show time separately
                    show_match = re.search(r"Show:\s*(\d+:?\d*\s*[APM]{2})", time_str)
                    if show_match:
                        time_str = show_match.group(1).strip()
                    
                    # Parse doors time to UTC
                    try:
                        # Normalize time format
                        doors_time = doors_time.replace(".", "").strip()
                        if ":" not in doors_time:
                            # Handle format like "8PM" -> "8:00PM"
                            time_parts = re.match(r"(\d+)\s*([APM]{2})", doors_time)
                            if time_parts:
                                hour, ampm = time_parts.groups()
                                doors_time = f"{hour}:00{ampm}"
                        
                        # Parse the date and doors time
                        dt_str = f"{date_str} {doors_time}"
                        dt_format = "%A, %B %d, %Y %I:%M%p"
                        local_tz = ZoneInfo(self.tz_name)
                        dt_local = datetime.strptime(dt_str, dt_format).replace(tzinfo=local_tz)
                        doors_time_utc = dt_local.astimezone(datetime.UTC).isoformat().replace("+00:00", "Z")
                    except Exception:
                        # If parsing fails, leave as None
                        doors_time_utc = None
            
            # Parse the event start time
            starts_at_utc = None
            try:
                # Clean up time string if it contains "Show:" prefix
                if "Show:" in time_str:
                    time_str = re.search(r"Show:\s*(\d+:?\d*\s*[APM]{2})", time_str).group(1).strip()
                else:
                    time_str = time_str.strip()
                
                # Normalize time format
                time_str = time_str.replace(".", "").strip()
                if ":" not in time_str:
                    # Handle format like "8PM" -> "8:00PM"
                    time_parts = re.match(r"(\d+)\s*([APM]{2})", time_str)
                    if time_parts:
                        hour, ampm = time_parts.groups()
                        time_str = f"{hour}:00{ampm}"
                
                # Parse the date and time
                dt_str = f"{date_str} {time_str}"
                dt_format = "%A, %B %d, %Y %I:%M%p"
                local_tz = ZoneInfo(self.tz_name)
                dt_local = datetime.strptime(dt_str, dt_format).replace(tzinfo=local_tz)
                starts_at_utc = dt_local.astimezone(datetime.UTC).isoformat().replace("+00:00", "Z")
            except Exception:
                # If we can't parse the time, skip this event
                continue
            
            # Extract price information
            price_node = event_node.css_first(".price")
            price_txt = price_node.text(strip=True) if price_node else ""
            price_min = price_max = None
            
            if price_txt:
                # Remove any non-price text
                price_txt = price_txt.replace("Price:", "").strip()
                
                if "–" in price_txt or "-" in price_txt:
                    # Handle price range
                    p = price_txt.replace("$", "").replace("–", "-").split("-")
                    try:
                        price_min = float(p[0].strip())
                        price_max = float(p[1].strip())
                    except Exception:
                        pass
                elif price_txt.lower() == "free":
                    price_min = price_max = 0.0
                elif "$" in price_txt:
                    # Handle single price
                    try:
                        price_match = re.search(r"\$(\d+(?:\.\d+)?)", price_txt)
                        if price_match:
                            price_min = price_max = float(price_match.group(1))
                    except Exception:
                        pass
            
            # Extract ticket URL
            ticket_link = event_node.css_first("a.tickets")
            ticket_url = ticket_link.attributes.get("href") if ticket_link else None
            
            # Extract age restriction
            age_node = event_node.css_first(".ageRestriction")
            age_restriction = age_node.text(strip=True) if age_node else None
            if age_restriction:
                age_restriction = age_restriction.replace("Age Restriction:", "").strip()
            
            # Check if event is cancelled
            is_cancelled = False
            status_node = event_node.css_first(".status")
            if status_node and "cancelled" in status_node.text(strip=True).lower():
                is_cancelled = True
            
            # Extract event ID if available
            event_id_node = event_node.css_first("[data-event-id]")
            external_id = event_id_node.attributes.get("data-event-id") if event_id_node else None
            
            # Extract description if available
            desc_node = event_node.css_first(".description")
            description = desc_node.text(strip=True) if desc_node else None
            
            # Create raw data for provenance
            raw_data = {
                "description": description,
                "full_date_text": date_str,
                "full_time_text": time_node.text(strip=True) if time_node else None
            }
            
            events.append(ExtractResult(
                site_slug=self.site_slug,
                venue_name="Music Farm",
                title=title,
                artist_name=artist_name,
                starts_at_utc=starts_at_utc,
                ends_at_utc=None,  # Music Farm doesn't typically list end times
                tz_name=self.tz_name,
                doors_time_utc=doors_time_utc,
                price_min=price_min,
                price_max=price_max,
                currency="USD",
                ticket_url=ticket_url,
                age_restriction=age_restriction,
                is_cancelled=is_cancelled,
                source_url=self.source_url,
                external_id=external_id,
                raw_data=raw_data
            ))

        return events