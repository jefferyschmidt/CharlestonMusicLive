"""
Generic Venue Extractor

A flexible extractor that can handle various venue website structures
by analyzing the page content and adapting to different layouts.
"""
import re
import logging
from datetime import datetime, timedelta
from typing import List, Optional, Dict, Any
from selectolax.parser import HTMLParser
from zoneinfo import ZoneInfo

from .base import Extractor, ExtractResult

logger = logging.getLogger(__name__)


class GenericVenueExtractor(Extractor):
    """Generic extractor that adapts to different venue website structures."""
    
    def __init__(self, site_slug: str, source_url: str, venue_type: str = "generic"):
        super().__init__(site_slug, source_url)
        self.venue_type = venue_type
        self.custom_selectors = {}
        self.date_patterns = []
        self.price_patterns = []
        
    def apply_configuration(self, config: Dict[str, Any]):
        """Apply custom configuration from the extractor factory."""
        self.custom_selectors = config.get('custom_selectors', {})
        self.date_patterns = config.get('date_patterns', [])
        self.price_patterns = config.get('price_patterns', [])
    
    def parse(self, html: str) -> List[ExtractResult]:
        """Parse events from venue HTML using adaptive selectors."""
        tree = HTMLParser(html)
        events: List[ExtractResult] = []
        
        # Try multiple event container selectors
        event_containers = self._find_event_containers(tree)
        
        for container in event_containers:
            try:
                event = self._extract_event_from_container(container)
                if event:
                    events.append(event)
            except Exception as e:
                logger.debug(f"Error extracting event from container: {e}")
                continue
        
        logger.info(f"Extracted {len(events)} events from {self.source_url}")
        return events
    
    def _find_event_containers(self, tree: HTMLParser) -> List[Any]:
        """Find event containers using multiple selector strategies."""
        containers = []
        
        # Priority 1: Custom selectors from configuration
        if self.custom_selectors.get('event_container'):
            for selector in self.custom_selectors['event_container']:
                containers.extend(tree.css(selector))
                if containers:
                    break
        
        # Priority 2: Common event container patterns
        if not containers:
            common_selectors = [
                '.event', '.show', '.performance', '.gig', '.concert',
                '.event-item', '.show-item', '.performance-item',
                'article', '.card', '.item', '.listing',
                '[class*="event"]', '[class*="show"]', '[class*="concert"]'
            ]
            
            for selector in common_selectors:
                containers.extend(tree.css(selector))
                if len(containers) > 5:  # Found enough containers
                    break
        
        # Priority 3: Look for repeated structures with dates
        if not containers:
            containers = self._find_structures_with_dates(tree)
        
        return containers
    
    def _find_structures_with_dates(self, tree: HTMLParser) -> List[Any]:
        """Find HTML structures that contain dates (likely event containers)."""
        containers = []
        
        # Look for elements containing date-like text
        date_elements = tree.css('*')
        date_containers = []
        
        for element in date_elements:
            text = element.text(strip=True)
            if self._contains_date(text):
                # Find the parent container that likely contains the full event
                parent = element.parent
                if parent and parent not in date_containers:
                    date_containers.append(parent)
        
        # Group by similar structure
        if date_containers:
            containers = self._group_similar_structures(date_containers)
        
        return containers
    
    def _group_similar_structures(self, elements: List[Any]) -> List[Any]:
        """Group elements with similar HTML structure."""
        if len(elements) <= 1:
            return elements
        
        # Simple grouping by tag name and class similarity
        groups = {}
        for element in elements:
            key = f"{element.tag}-{element.attributes.get('class', '')[:20]}"
            if key not in groups:
                groups[key] = []
            groups[key].append(element)
        
        # Return the largest group
        largest_group = max(groups.values(), key=len)
        return largest_group
    
    def _extract_event_from_container(self, container: Any) -> Optional[ExtractResult]:
        """Extract event data from a single container."""
        try:
            # Extract title/artist
            title = self._extract_title(container)
            if not title:
                return None
            
            # Extract date and time
            date_info = self._extract_date_time(container)
            if not date_info:
                return None
            
            # Extract other fields
            venue_name = self._extract_venue_name(container)
            price_info = self._extract_price(container)
            ticket_url = self._extract_ticket_url(container)
            external_id = self._extract_external_id(container)
            
            # Create event
            event = ExtractResult(
                site_slug=self.site_slug,
                venue_name=venue_name,
                title=title,
                artist_name=title,  # For now, assume title is artist name
                starts_at_utc=date_info['starts_at_utc'],
                ends_at_utc=date_info['ends_at_utc'],
                tz_name=self.tz_name,
                doors_time_utc=date_info['doors_time_utc'],
                price_min=price_info.get('min'),
                price_max=price_info.get('max'),
                currency="USD",
                ticket_url=ticket_url,
                age_restriction=None,
                is_cancelled=False,
                source_url=self.source_url,
                external_id=external_id,
                raw_data=self._extract_raw_data(container)
            )
            
            return event
            
        except Exception as e:
            logger.debug(f"Error extracting event: {e}")
            return None
    
    def _extract_title(self, container: Any) -> Optional[str]:
        """Extract event title from container."""
        # Try custom selectors first
        if self.custom_selectors.get('title'):
            for selector in self.custom_selectors['title']:
                element = container.css_first(selector)
                if element:
                    title = element.text(strip=True)
                    if title:
                        return title
        
        # Try common title patterns
        title_selectors = [
            'h1', 'h2', 'h3', 'h4', 'h5', 'h6',
            '.title', '.name', '.event-title', '.show-title',
            '.artist-name', '.performer', '.band-name',
            '[class*="title"]', '[class*="name"]'
        ]
        
        for selector in title_selectors:
            element = container.css_first(selector)
            if element:
                title = element.text(strip=True)
                if title and len(title) > 3:  # Avoid very short titles
                    return title
        
        return None
    
    def _extract_date_time(self, container: Any) -> Optional[Dict[str, str]]:
        """Extract date and time information."""
        # Try custom selectors first
        if self.custom_selectors.get('date'):
            for selector in self.custom_selectors['date']:
                element = container.css_first(selector)
                if element:
                    date_text = element.text(strip=True)
                    parsed = self._parse_date_time(date_text)
                    if parsed:
                        return parsed
        
        # Try common date patterns
        date_selectors = [
            '.date', '.time', '.when', '.datetime', '.show-time',
            '.event-date', '.performance-date', '.concert-date',
            '[class*="date"]', '[class*="time"]'
        ]
        
        for selector in date_selectors:
            element = container.css_first(selector)
            if element:
                date_text = element.text(strip=True)
                parsed = self._parse_date_time(date_text)
                if parsed:
                    return parsed
        
        return None
    
    def _parse_date_time(self, date_text: str) -> Optional[Dict[str, str]]:
        """Parse date and time text into structured format."""
        if not date_text:
            return None
        
        try:
            # Try various date formats
            date_formats = [
                # "August 27, 2025" or "Aug 27, 2025"
                r'(\w+)\s+(\d{1,2}),?\s+(\d{4})',
                # "8/27/2025" or "08/27/2025"
                r'(\d{1,2})/(\d{1,2})/(\d{4})',
                # "2025-08-27"
                r'(\d{4})-(\d{1,2})-(\d{1,2})',
                # "27 Aug 2025"
                r'(\d{1,2})\s+(\w+)\s+(\d{4})'
            ]
            
            for pattern in date_formats:
                match = re.search(pattern, date_text, re.IGNORECASE)
                if match:
                    if len(match.groups()) == 3:
                        if pattern == date_formats[0]:  # "August 27, 2025"
                            month_name, day, year = match.groups()
                            month = self._month_name_to_number(month_name)
                            if month:
                                # Assume 8 PM show time for now
                                dt = datetime(int(year), month, int(day), 20, 0)
                                # Assume EST (UTC-5) for Charleston
                                est_offset = timedelta(hours=5)
                                dt_utc = dt - est_offset
                                
                                return {
                                    'starts_at_utc': dt_utc.isoformat(),
                                    'ends_at_utc': None,
                                    'doors_time_utc': None
                                }
            
            return None
            
        except Exception as e:
            logger.debug(f"Error parsing date '{date_text}': {e}")
            return None
    
    def _month_name_to_number(self, month_name: str) -> Optional[int]:
        """Convert month name to number."""
        months = {
            'january': 1, 'jan': 1,
            'february': 2, 'feb': 2,
            'march': 3, 'mar': 3,
            'april': 4, 'apr': 4,
            'may': 5,
            'june': 6, 'jun': 6,
            'july': 7, 'jul': 7,
            'august': 8, 'aug': 8,
            'september': 9, 'sep': 9,
            'october': 10, 'oct': 10,
            'november': 11, 'nov': 11,
            'december': 12, 'dec': 12
        }
        return months.get(month_name.lower())
    
    def _extract_venue_name(self, container: Any) -> str:
        """Extract venue name."""
        # Try to get from the page title or fall back to domain
        from urllib.parse import urlparse
        domain = urlparse(self.source_url).netloc
        return domain.replace('www.', '').replace('.com', '').title()
    
    def _extract_price(self, container: Any) -> Dict[str, Optional[float]]:
        """Extract price information."""
        # Try custom selectors first
        if self.custom_selectors.get('price'):
            for selector in self.custom_selectors['price']:
                element = container.css_first(selector)
                if element:
                    price_text = element.text(strip=True)
                    parsed = self._parse_price(price_text)
                    if parsed:
                        return parsed
        
        # Try common price patterns
        price_selectors = [
            '.price', '.cost', '.ticket-price', '.admission',
            '[class*="price"]', '[class*="cost"]'
        ]
        
        for selector in price_selectors:
            element = container.css_first(selector)
            if element:
                price_text = element.text(strip=True)
                parsed = self._parse_price(price_text)
                if parsed:
                    return parsed
        
        return {'min': None, 'max': None}
    
    def _parse_price(self, price_text: str) -> Optional[Dict[str, Optional[float]]]:
        """Parse price text into min/max values."""
        if not price_text:
            return None
        
        try:
            # Remove currency symbols and clean up
            clean_text = re.sub(r'[^\d\-–.]', '', price_text)
            
            if '–' in clean_text or '-' in clean_text:
                parts = clean_text.replace('–', '-').split('-')
                if len(parts) == 2:
                    min_price = float(parts[0]) if parts[0] else None
                    max_price = float(parts[1]) if parts[1] else None
                    return {'min': min_price, 'max': max_price}
            else:
                price = float(clean_text) if clean_text else None
                return {'min': price, 'max': price}
            
        except Exception as e:
            logger.debug(f"Error parsing price '{price_text}': {e}")
        
        return None
    
    def _extract_ticket_url(self, container: Any) -> Optional[str]:
        """Extract ticket purchase URL."""
        # Look for ticket-related links
        ticket_selectors = [
            'a[href*="ticket"]', 'a[href*="buy"]', 'a[href*="purchase"]',
            '.tickets a', '.buy-tickets a', '.purchase a'
        ]
        
        for selector in ticket_selectors:
            element = container.css_first(selector)
            if element:
                href = element.attributes.get('href')
                if href:
                    return href
        
        return None
    
    def _extract_external_id(self, container: Any) -> Optional[str]:
        """Extract external ID if available."""
        # Look for data attributes or IDs that might be external references
        external_id = container.attributes.get('data-event-id') or \
                     container.attributes.get('data-show-id') or \
                     container.attributes.get('id')
        return external_id
    
    def _extract_raw_data(self, container: Any) -> Optional[Dict[str, Any]]:
        """Extract additional raw data for storage."""
        raw_data = {}
        
        # Extract description if available
        desc_selectors = ['.description', '.desc', '.details', '[class*="desc"]']
        for selector in desc_selectors:
            element = container.css_first(selector)
            if element:
                desc = element.text(strip=True)
                if desc:
                    raw_data['description'] = desc
                    break
        
        # Extract age restriction if available
        age_selectors = ['.age', '.age-restriction', '[class*="age"]']
        for selector in age_selectors:
            element = container.css_first(selector)
            if element:
                age = element.text(strip=True)
                if age:
                    raw_data['age_restriction'] = age
                    break
        
        return raw_data if raw_data else None
    
    def _contains_date(self, text: str) -> bool:
        """Check if text contains date-like patterns."""
        if not text:
            return False
        
        # Simple date pattern matching
        date_patterns = [
            r'\b(?:january|february|march|april|may|june|july|august|september|october|november|december)\s+\d{1,2}',
            r'\b(?:jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec)\s+\d{1,2}',
            r'\d{1,2}/\d{1,2}/\d{4}',
            r'\d{4}-\d{2}-\d{2}'
        ]
        
        for pattern in date_patterns:
            if re.search(pattern, text, re.IGNORECASE):
                return True
        
        return False
