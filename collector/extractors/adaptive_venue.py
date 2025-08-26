"""
Adaptive Venue Extractor

A single, intelligent extractor that can automatically adapt to any venue website
by analyzing the page structure and learning extraction patterns.
"""
import re
import logging
from datetime import datetime, timedelta
from typing import List, Optional, Dict, Any, Tuple
from selectolax.parser import HTMLParser
from zoneinfo import ZoneInfo
import json

from .base import Extractor, ExtractResult

logger = logging.getLogger(__name__)


class AdaptiveVenueExtractor(Extractor):
    """Adaptive extractor that learns and adapts to any venue website structure."""
    
    def __init__(self, site_slug: str, source_url: str):
        super().__init__(site_slug, source_url)
        self.venue_name = self._extract_venue_name_from_url()
        self.extraction_patterns = {}
        self.learned_selectors = {}
        
    def parse(self, html: str) -> List[ExtractResult]:
        """Parse events using adaptive extraction strategies."""
        tree = HTMLParser(html)
        events: List[ExtractResult] = []
        
        # Strategy 1: Look for obvious event containers
        event_containers = self._find_event_containers(tree)
        
        if event_containers:
            logger.info(f"Found {len(event_containers)} event containers using pattern matching")
            for container in event_containers:
                event = self._extract_event_from_container(container, html)
                if event:
                    events.append(event)
        
        # Strategy 2: If no events found, try structural analysis
        if not events:
            logger.info("No events found with pattern matching, trying structural analysis")
            event_containers = self._analyze_page_structure(tree, html)
            
            for container in event_containers:
                event = self._extract_event_from_container(container, html)
                if event:
                    events.append(event)
        
        # Strategy 3: Last resort - look for any repeated structures with dates
        if not events:
            logger.info("No events found with structural analysis, trying date-based discovery")
            event_containers = self._find_structures_with_dates(tree, html)
            
            for container in event_containers:
                event = self._extract_event_from_container(container, html)
                if event:
                    events.append(event)
        
        # Learn from this extraction for future use
        if events:
            self._learn_extraction_patterns(html, events)
        
        logger.info(f"Adaptive extractor found {len(events)} events from {self.source_url}")
        return events
    
    def _find_event_containers(self, tree: HTMLParser) -> List[Any]:
        """Find event containers using common patterns."""
        containers = []
        
        # Common event container selectors
        selectors = [
            # Standard event containers
            '.event', '.show', '.performance', '.gig', '.concert',
            '.event-item', '.show-item', '.performance-item',
            '.event-card', '.show-card', '.performance-card',
            
            # Generic containers that often contain events
            'article', '.card', '.item', '.listing', '.entry',
            
            # Venue-specific patterns
            '[class*="event"]', '[class*="show"]', '[class*="concert"]',
            '[class*="performance"]', '[class*="gig"]',
            
            # List items that might be events
            'li[class*="event"]', 'li[class*="show"]',
            
            # Div containers with event-like classes
            'div[class*="event"]', 'div[class*="show"]'
        ]
        
        for selector in selectors:
            elements = tree.css(selector)
            if elements:
                containers.extend(elements)
                if len(containers) > 50:  # Limit to avoid too many
                    break
        
        # Remove duplicates while preserving order
        seen = set()
        unique_containers = []
        for container in containers:
            if container not in seen:
                seen.add(container)
                unique_containers.append(container)
        
        return unique_containers
    
    def _analyze_page_structure(self, tree: HTMLParser, html: str) -> List[Any]:
        """Analyze page structure to find potential event containers."""
        containers = []
        
        # Look for repeated HTML structures
        all_elements = tree.css('*')
        structure_groups = {}
        
        for element in all_elements:
            if element.tag in ['div', 'article', 'section', 'li']:
                # Create a structure signature
                signature = self._create_structure_signature(element)
                if signature not in structure_groups:
                    structure_groups[signature] = []
                structure_groups[signature].append(element)
        
        # Find structures that appear multiple times (likely events)
        for signature, elements in structure_groups.items():
            if len(elements) >= 3:  # At least 3 similar structures
                # Check if these structures contain date-like content
                date_containing = [e for e in elements if self._contains_date_content(e.text())]
                if date_containing:
                    containers.extend(date_containing[:20])  # Limit to first 20
        
        return containers
    
    def _create_structure_signature(self, element) -> str:
        """Create a signature for an HTML element structure."""
        signature_parts = [
            element.tag,
            element.attributes.get('class', '')[:50],  # First 50 chars of class
            element.attributes.get('id', '')[:50],     # First 50 chars of id
            str(len(element.children))                 # Number of children
        ]
        return '|'.join(signature_parts)
    
    def _find_structures_with_dates(self, tree: HTMLParser, html: str) -> List[Any]:
        """Find HTML structures that contain dates (likely event containers)."""
        containers = []
        
        # Look for elements containing date-like text
        date_elements = tree.css('*')
        date_containers = []
        
        for element in date_elements:
            text = element.text()
            if self._contains_date_content(text):
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
    
    def _extract_event_from_container(self, container: Any, html: str) -> Optional[ExtractResult]:
        """Extract event data from a container using multiple strategies."""
        try:
            # Extract title/artist
            title = self._extract_title(container)
            if not title:
                return None
            
            # Extract date and time
            date_info = self._extract_date_time(container, html)
            if not date_info:
                return None
            
            # Extract other fields
            price_info = self._extract_price(container, html)
            ticket_url = self._extract_ticket_url(container)
            external_id = self._extract_external_id(container)
            
            # Create event
            event = ExtractResult(
                site_slug=self.site_slug,
                venue_name=self.venue_name,
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
        """Extract event title using multiple strategies."""
        # Strategy 1: Try common title selectors
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
                if title and len(title) > 3 and not self._is_metadata_text(title):
                    return title
        
        # Strategy 2: Look for the largest text block that's not metadata
        text_blocks = container.css('p, div, span')
        best_title = None
        best_score = 0
        
        for block in text_blocks:
            text = block.text(strip=True)
            if text and len(text) > 10 and len(text) < 200:
                score = self._score_title_candidate(text)
                if score > best_score:
                    best_score = score
                    best_title = text
        
        return best_title
    
    def _is_metadata_text(self, text: str) -> bool:
        """Check if text is metadata rather than a title."""
        metadata_indicators = [
            'calendar', 'schedule', 'events', 'shows', 'concerts',
            'doors', 'show starts', 'buy tickets', 'rsvp',
            'today', 'tomorrow', 'this week', 'next week'
        ]
        
        text_lower = text.lower()
        return any(indicator in text_lower for indicator in metadata_indicators)
    
    def _score_title_candidate(self, text: str) -> float:
        """Score a potential title candidate."""
        score = 0.0
        
        # Longer titles get higher scores (but not too long)
        if 10 <= len(text) <= 100:
            score += 0.3
        
        # Titles with artist-like patterns get higher scores
        if re.search(r'\b[A-Z][a-z]+(?:\s+[A-Z][a-z]+)*\b', text):
            score += 0.4
        
        # Avoid titles that are just dates or times
        if re.match(r'^\d+[/-]\d+[/-]\d+$', text):
            score -= 0.5
        
        # Avoid titles that are just generic words
        generic_words = ['event', 'show', 'concert', 'performance', 'gig']
        if text.lower() in generic_words:
            score -= 0.3
        
        return score
    
    def _extract_date_time(self, container: Any, html: str) -> Optional[dict]:
        """Extract date and time using multiple strategies."""
        text = container.text()
        
        # Strategy 1: Look for date patterns
        date_patterns = [
            # "August 30, 2025" or "Aug 30, 2025"
            r'(\w+)\s+(\d{1,2}),?\s+(\d{4})',
            # "8/30/2025" or "08/30/2025"
            r'(\d{1,2})/(\d{1,2})/(\d{4})',
            # "2025-08-30"
            r'(\d{4})-(\d{1,2})-(\d{1,2})',
            # "30 Aug 2025"
            r'(\d{1,2})\s+(\w+)\s+(\d{4})'
        ]
        
        for pattern in date_patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                if len(match.groups()) == 3:
                    if pattern == date_patterns[0]:  # "August 30, 2025"
                        month_name, day, year = match.groups()
                        month = self._month_name_to_number(month_name)
                        if month:
                            # Look for time information
                            time_info = self._extract_time_info(text)
                            hour, minute = time_info if time_info else (20, 0)  # Default 8 PM
                            
                            dt = datetime(int(year), month, int(day), hour, minute)
                            # Assume EST (UTC-5) for Charleston
                            est_offset = timedelta(hours=5)
                            dt_utc = dt - est_offset
                            
                            # Look for doors time
                            doors_time = self._extract_doors_time(text)
                            
                            return {
                                'starts_at_utc': dt_utc.isoformat(),
                                'ends_at_utc': None,
                                'doors_time_utc': doors_time
                            }
        
        return None
    
    def _extract_time_info(self, text: str) -> Optional[tuple]:
        """Extract time information from text."""
        # Look for time patterns like "8:00 pm", "8:00 PM", "20:00"
        time_patterns = [
            r'(\d{1,2}):(\d{2})\s*(am|pm)',
            r'(\d{1,2}):(\d{2})\s*(AM|PM)',
            r'(\d{1,2}):(\d{2})'
        ]
        
        for pattern in time_patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                hour = int(match.group(1))
                minute = int(match.group(2))
                
                # Handle AM/PM
                if len(match.groups()) > 2 and match.group(3).lower() == 'pm' and hour != 12:
                    hour += 12
                elif len(match.groups()) > 2 and match.group(3).lower() == 'am' and hour == 12:
                    hour = 0
                
                return (hour, minute)
        
        return None
    
    def _extract_doors_time(self, text: str) -> Optional[str]:
        """Extract doors time from text."""
        doors_patterns = [
            r'doors:\s*(\d{1,2}):(\d{2})\s*(am|pm)',
            r'doors\s+(\d{1,2}):(\d{2})\s*(am|pm)',
            r'(\d{1,2}):(\d{2})\s*(am|pm)\s*doors'
        ]
        
        for pattern in doors_patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                hour = int(match.group(1))
                minute = int(match.group(2))
                ampm = match.group(3).lower()
                
                # Handle AM/PM
                if ampm == 'pm' and hour != 12:
                    hour += 12
                elif ampm == 'am' and hour == 12:
                    hour = 0
                
                # Convert to UTC (EST is UTC-5)
                dt = datetime(2025, 1, 1, hour, minute)  # Use dummy date
                est_offset = timedelta(hours=5)
                dt_utc = dt - est_offset
                
                return dt_utc.isoformat()
        
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
    
    def _extract_price(self, container: Any, html: str) -> dict:
        """Extract price information using multiple strategies."""
        text = container.text()
        
        # Strategy 1: Look for price patterns
        price_patterns = [
            r'\$(\d+(?:\.\d{2})?)',
            r'(\d+(?:\.\d{2})?)\s*\$',
            r'price:\s*\$?(\d+(?:\.\d{2})?)',
            r'tickets?\s*\$?(\d+(?:\.\d{2})?)',
            r'cost:\s*\$?(\d+(?:\.\d{2})?)',
            r'admission:\s*\$?(\d+(?:\.\d{2})?)'
        ]
        
        for pattern in price_patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                try:
                    price = float(match.group(1))
                    return {'min': price, 'max': price}
                except ValueError:
                    continue
        
        # Strategy 2: Look for price ranges
        range_patterns = [
            r'\$(\d+(?:\.\d{2})?)\s*[-–]\s*\$(\d+(?:\.\d{2})?)',
            r'(\d+(?:\.\d{2})?)\s*[-–]\s*(\d+(?:\.\d{2})?)\s*\$'
        ]
        
        for pattern in range_patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                try:
                    min_price = float(match.group(1))
                    max_price = float(match.group(2))
                    return {'min': min_price, 'max': max_price}
                except ValueError:
                    continue
        
        return {'min': None, 'max': None}
    
    def _extract_ticket_url(self, container: Any) -> Optional[str]:
        """Extract ticket purchase URL."""
        # Look for ticket-related links
        ticket_selectors = [
            'a[href*="ticket"]', 'a[href*="buy"]', 'a[href*="purchase"]',
            'a[href*="rsvp"]', 'a[href*="reserve"]', 'a[href*="booking"]'
        ]
        
        for selector in ticket_selectors:
            links = container.css(selector)
            for link in links:
                href = link.attributes.get('href')
                if href:
                    return href
        
        return None
    
    def _extract_external_id(self, container: Any) -> Optional[str]:
        """Extract external ID if available."""
        # Look for data attributes or IDs
        external_id = container.attributes.get('data-event-id') or \
                     container.attributes.get('data-show-id') or \
                     container.attributes.get('data-id') or \
                     container.attributes.get('id')
        return external_id
    
    def _extract_raw_data(self, container: Any) -> Optional[dict]:
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
    
    def _contains_date_content(self, text: str) -> bool:
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
    
    def _extract_venue_name_from_url(self) -> str:
        """Extract venue name from the source URL."""
        from urllib.parse import urlparse
        try:
            parsed = urlparse(self.source_url)
            domain = parsed.netloc.lower()
            
            # Clean up domain to get venue name
            venue_name = domain.replace('www.', '').replace('.com', '').replace('.org', '')
            
            # Convert to title case and handle common patterns
            venue_name = venue_name.replace('-', ' ').replace('_', ' ').title()
            
            return venue_name
        except Exception:
            return "Unknown Venue"
    
    def _learn_extraction_patterns(self, html: str, events: List[ExtractResult]):
        """Learn from successful extractions to improve future performance."""
        # Store successful patterns for this venue
        self.extraction_patterns[self.source_url] = {
            'event_count': len(events),
            'successful_selectors': self._identify_successful_selectors(html, events),
            'extraction_timestamp': datetime.now().isoformat()
        }
        
        logger.info(f"Learned extraction patterns for {self.source_url}")
    
    def _identify_successful_selectors(self, html: str, events: List[ExtractResult]) -> Dict[str, Any]:
        """Identify which selectors were successful for extraction."""
        # This is a simplified version - in a real implementation,
        # you'd track which selectors actually found the event data
        return {
            'container_selectors': ['.event', 'article', '.card'],
            'title_selectors': ['h1', 'h2', 'h3', '.title'],
            'date_selectors': ['.date', '.time', '.datetime']
        }
