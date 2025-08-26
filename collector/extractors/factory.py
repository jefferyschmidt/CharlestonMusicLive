"""
Intelligent Extractor Factory

Automatically selects and configures the appropriate extractor for discovered sources
based on their characteristics, structure, and content patterns.
"""
import logging
from typing import Optional, Dict, Any, List
from dataclasses import dataclass
from urllib.parse import urlparse
import re
from bs4 import BeautifulSoup

from .base import Extractor, ExtractResult
from .sample_venue import SampleVenueExtractor
from .music_farm import MusicFarmExtractor

logger = logging.getLogger(__name__)


@dataclass
class ExtractorMatch:
    """Represents a match between a source and an extractor."""
    extractor_class: type
    confidence_score: float
    reasoning: str
    configuration: Dict[str, Any]


class ExtractorFactory:
    """Factory for creating appropriate extractors for discovered sources."""
    
    def __init__(self):
        # Available extractors with their characteristics
        self.extractors = {
            'sample_venue': {
                'class': SampleVenueExtractor,
                'patterns': ['sample', 'test', 'fixture'],
                'confidence': 0.8
            },
            'music_farm': {
                'class': MusicFarmExtractor,
                'patterns': ['music farm', 'musicfarm'],
                'confidence': 0.9
            }
        }
        
        # Common venue patterns for generic extractors
        self.venue_patterns = {
            'concert_venue': {
                'indicators': ['concert', 'venue', 'theater', 'amphitheater', 'arena'],
                'confidence': 0.7
            },
            'bar_venue': {
                'indicators': ['bar', 'pub', 'tavern', 'lounge', 'club'],
                'confidence': 0.6
            },
            'restaurant_venue': {
                'indicators': ['restaurant', 'cafe', 'bistro', 'grill', 'kitchen'],
                'confidence': 0.6
            },
            'outdoor_venue': {
                'indicators': ['park', 'plaza', 'square', 'beach', 'outdoor'],
                'confidence': 0.5
            }
        }
    
    def analyze_source(self, url: str, html: str, metadata: Dict[str, Any]) -> ExtractorMatch:
        """Analyze a source and determine the best extractor to use."""
        soup = BeautifulSoup(html, 'html.parser')
        
        # Check for exact matches with known extractors
        exact_match = self._find_exact_match(url, html, metadata)
        if exact_match:
            return exact_match
        
        # Analyze the page structure to determine venue type
        venue_type = self._analyze_venue_type(soup, html, metadata)
        
        # Create a generic extractor based on venue type
        return self._create_generic_extractor(venue_type, url, metadata)
    
    def _find_exact_match(self, url: str, html: str, metadata: Dict[str, Any]) -> Optional[ExtractorMatch]:
        """Find exact matches with known extractors."""
        url_lower = url.lower()
        html_lower = html.lower()
        
        for extractor_name, extractor_info in self.extractors.items():
            for pattern in extractor_info['patterns']:
                if pattern in url_lower or pattern in html_lower:
                    return ExtractorMatch(
                        extractor_class=extractor_info['class'],
                        confidence_score=extractor_info['confidence'],
                        reasoning=f"Exact match with {extractor_name} extractor",
                        configuration={}
                    )
        
        return None
    
    def _analyze_venue_type(self, soup: BeautifulSoup, html: str, metadata: Dict[str, Any]) -> str:
        """Analyze the page to determine the type of venue."""
        text = soup.get_text().lower()
        html_lower = html.lower()
        
        # Check for venue type indicators
        venue_scores = {}
        
        for venue_type, pattern_info in self.venue_patterns.items():
            score = 0.0
            for indicator in pattern_info['indicators']:
                # Count occurrences in text and HTML
                text_count = text.count(indicator)
                html_count = html_lower.count(indicator)
                
                # Weight HTML occurrences more heavily (likely in class names, IDs)
                score += text_count * 0.1 + html_count * 0.2
            
            venue_scores[venue_type] = score
        
        # Check for specific venue characteristics
        if self._has_calendar_structure(soup, html):
            venue_scores['concert_venue'] += 0.3
        
        if self._has_ticketing_system(html):
            venue_scores['concert_venue'] += 0.2
        
        if self._has_food_menu(soup, html):
            venue_scores['restaurant_venue'] += 0.3
        
        if self._has_drink_menu(soup, html):
            venue_scores['bar_venue'] += 0.3
        
        # Return the venue type with the highest score
        if venue_scores:
            best_type = max(venue_scores, key=venue_scores.get)
            if venue_scores[best_type] > 0.5:
                return best_type
        
        return 'generic_venue'
    
    def _has_calendar_structure(self, soup: BeautifulSoup, html: str) -> bool:
        """Check if the page has a calendar-like structure."""
        calendar_indicators = [
            'calendar', 'datepicker', 'month', 'week', 'day',
            'event-calendar', 'schedule', 'upcoming', 'events'
        ]
        
        for indicator in calendar_indicators:
            if indicator in html.lower():
                return True
        
        # Check for date-like elements
        date_elements = soup.find_all(['time', 'span', 'div'], 
                                    class_=re.compile(r'date|time|calendar', re.I))
        if len(date_elements) > 2:
            return True
        
        return False
    
    def _has_ticketing_system(self, html: str) -> bool:
        """Check if the page has ticketing functionality."""
        ticketing_indicators = [
            'buy tickets', 'get tickets', 'purchase tickets',
            'ticket', 'rsvp', 'reserve', 'booking'
        ]
        
        for indicator in ticketing_indicators:
            if indicator in html.lower():
                return True
        
        return False
    
    def _has_food_menu(self, soup: BeautifulSoup, html: str) -> bool:
        """Check if the page has food menu information."""
        food_indicators = [
            'menu', 'appetizer', 'entree', 'dessert', 'breakfast',
            'lunch', 'dinner', 'chef', 'kitchen', 'cuisine'
        ]
        
        for indicator in food_indicators:
            if indicator in html.lower():
                return True
        
        return False
    
    def _has_drink_menu(self, soup: BeautifulSoup, html: str) -> bool:
        """Check if the page has drink menu information."""
        drink_indicators = [
            'cocktail', 'beer', 'wine', 'spirits', 'drinks',
            'bar menu', 'happy hour', 'specialty drinks'
        ]
        
        for indicator in drink_indicators:
            if indicator in html.lower():
                return True
        
        return False
    
    def _create_generic_extractor(self, venue_type: str, url: str, metadata: Dict[str, Any]) -> ExtractorMatch:
        """Create a generic extractor based on venue type."""
        # For now, use the sample venue extractor as a base
        # In the future, we could create specialized generic extractors
        
        configuration = {
            'venue_type': venue_type,
            'custom_selectors': self._generate_custom_selectors(venue_type),
            'date_patterns': self._get_date_patterns(venue_type),
            'price_patterns': self._get_price_patterns(venue_type)
        }
        
        return ExtractorMatch(
            extractor_class=SampleVenueExtractor,  # Use as base for now
            confidence_score=0.6,
            reasoning=f"Generic extractor for {venue_type} venue type",
            configuration=configuration
        )
    
    def _generate_custom_selectors(self, venue_type: str) -> Dict[str, List[str]]:
        """Generate custom CSS selectors based on venue type."""
        base_selectors = {
            'event_container': ['.event', '.show', '.performance', '.gig'],
            'title': ['.title', '.name', '.event-title', 'h1', 'h2', 'h3'],
            'date': ['.date', '.time', '.when', '.datetime'],
            'price': ['.price', '.cost', '.ticket-price'],
            'venue': ['.venue', '.location', '.place']
        }
        
        # Customize selectors based on venue type
        if venue_type == 'concert_venue':
            base_selectors['event_container'].extend(['.concert', '.concert-item', '.show-item'])
            base_selectors['title'].extend(['.artist-name', '.performer'])
        
        elif venue_type == 'bar_venue':
            base_selectors['event_container'].extend(['.live-music', '.entertainment', '.event'])
            base_selectors['date'].extend(['.live-music-schedule', '.entertainment-schedule'])
        
        elif venue_type == 'restaurant_venue':
            base_selectors['event_container'].extend(['.special-event', '.dinner-show', '.live-entertainment'])
            base_selectors['date'].extend(['.event-schedule', '.special-events'])
        
        return base_selectors
    
    def _get_date_patterns(self, venue_type: str) -> List[str]:
        """Get date patterns appropriate for the venue type."""
        base_patterns = [
            r'\b(?:january|february|march|april|may|june|july|august|september|october|november|december)\s+\d{1,2}',
            r'\b(?:jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec)\s+\d{1,2}',
            r'\d{1,2}/\d{1,2}/\d{4}',
            r'\d{4}-\d{2}-\d{2}'
        ]
        
        if venue_type == 'concert_venue':
            base_patterns.extend([
                r'\b(?:doors|show starts|performance)\s+\d{1,2}:\d{2}\s*(?:AM|PM)',
                r'\b(?:doors|show starts|performance)\s+\d{1,2}:\d{2}'
            ])
        
        elif venue_type in ['bar_venue', 'restaurant_venue']:
            base_patterns.extend([
                r'\b(?:live music|entertainment)\s+(?:tonight|tomorrow|this week)',
                r'\b(?:live music|entertainment)\s+\d{1,2}:\d{2}\s*(?:PM|evening)'
            ])
        
        return base_patterns
    
    def _get_price_patterns(self, venue_type: str) -> List[str]:
        """Get price patterns appropriate for the venue type."""
        base_patterns = [
            r'\$\d+(?:\.\d{2})?',
            r'\$\d+(?:\.\d{2})?\s*[-–]\s*\$\d+(?:\.\d{2})?',
            r'(?:cover|admission|ticket)\s*\$?\d+(?:\.\d{2})?'
        ]
        
        if venue_type == 'concert_venue':
            base_patterns.extend([
                r'(?:general admission|VIP|premium)\s*\$?\d+(?:\.\d{2})?',
                r'(?:early bird|advance|day of)\s*\$?\d+(?:\.\d{2})?'
            ])
        
        elif venue_type in ['bar_venue', 'restaurant_venue']:
            base_patterns.extend([
                r'(?:no cover|free admission|complimentary)',
                r'(?:food minimum|drink minimum)\s*\$?\d+(?:\.\d{2})?'
            ])
        
        return base_patterns
    
    def create_extractor(self, match: ExtractorMatch, site_slug: str, source_url: str) -> Extractor:
        """Create an extractor instance based on the match."""
        extractor = match.extractor_class(site_slug=site_slug, source_url=source_url)
        
        # Apply custom configuration if available
        if hasattr(extractor, 'apply_configuration'):
            extractor.apply_configuration(match.configuration)
        
        return extractor


class AdaptiveExtractor(Extractor):
    """An adaptive extractor that learns from page structure."""
    
    def __init__(self, site_slug: str, source_url: str, configuration: Dict[str, Any]):
        super().__init__(site_slug, source_url)
        self.configuration = configuration
        self.venue_type = configuration.get('venue_type', 'generic_venue')
        self.custom_selectors = configuration.get('custom_selectors', {})
        self.date_patterns = configuration.get('date_patterns', [])
        self.price_patterns = configuration.get('price_patterns', [])
        
        # Learning state
        self.successful_patterns = []
        self.failed_patterns = []
        self.extraction_stats = {
            'total_attempts': 0,
            'successful_extractions': 0,
            'failed_extractions': 0
        }
    
    def parse(self, html_content: str) -> List[ExtractResult]:
        """Parse HTML content using adaptive patterns."""
        self.extraction_stats['total_attempts'] += 1
        
        try:
            events = self._extract_events(html_content)
            
            if events:
                self.extraction_stats['successful_extractions'] += 1
                # Learn from successful patterns
                self._learn_successful_patterns(html_content, events)
            else:
                self.extraction_stats['failed_extractions'] += 1
                # Learn from failed attempts
                self._learn_failed_patterns(html_content)
            
            return events
            
        except Exception as e:
            logger.error(f"Error in adaptive extraction: {e}")
            self.extraction_stats['failed_extractions'] += 1
            return []
    
    def _extract_events(self, html_content: str) -> List[ExtractResult]:
        """Extract events using current configuration."""
        soup = BeautifulSoup(html_content, 'html.parser')
        events = []
        
        # Try different extraction strategies
        strategies = [
            self._extract_by_container,
            self._extract_by_list,
            self._extract_by_table,
            self._extract_by_individual_elements
        ]
        
        for strategy in strategies:
            try:
                events = strategy(soup, html_content)
                if events:
                    break
            except Exception as e:
                logger.debug(f"Strategy {strategy.__name__} failed: {e}")
                continue
        
        return events
    
    def _extract_by_container(self, soup: BeautifulSoup, html: str) -> List[ExtractResult]:
        """Extract events by looking for event containers."""
        containers = []
        
        # Try custom selectors first
        for selector in self.custom_selectors.get('event_container', []):
            containers.extend(soup.select(selector))
        
        # Fall back to common patterns
        if not containers:
            common_selectors = [
                '[class*="event"]', '[class*="show"]', '[class*="performance"]',
                '[class*="gig"]', '[class*="concert"]', '[id*="event"]'
            ]
            for selector in common_selectors:
                containers.extend(soup.select(selector))
        
        events = []
        for container in containers[:20]:  # Limit to avoid too many
            event = self._extract_single_event(container, html)
            if event:
                events.append(event)
        
        return events
    
    def _extract_by_list(self, soup: BeautifulSoup, html: str) -> List[ExtractResult]:
        """Extract events by looking for list structures."""
        events = []
        
        # Look for list items that might contain events
        list_selectors = ['li', '.list-item', '[class*="list"]']
        
        for selector in list_selectors:
            items = soup.select(selector)
            for item in items[:30]:  # Limit items
                if self._looks_like_event(item, html):
                    event = self._extract_single_event(item, html)
                    if event:
                        events.append(event)
        
        return events
    
    def _extract_by_table(self, soup: BeautifulSoup, html: str) -> List[ExtractResult]:
        """Extract events from table structures."""
        events = []
        
        tables = soup.find_all('table')
        for table in tables:
            rows = table.find_all('tr')
            for row in rows[1:]:  # Skip header row
                if self._looks_like_event(row, html):
                    event = self._extract_single_event(row, html)
                    if event:
                        events.append(event)
        
        return events
    
    def _extract_by_individual_elements(self, soup: BeautifulSoup, html: str) -> List[ExtractResult]:
        """Extract events by looking for individual event elements."""
        events = []
        
        # Look for elements that might be events
        potential_elements = soup.find_all(['div', 'article', 'section'])
        
        for element in potential_elements[:50]:  # Limit elements
            if self._looks_like_event(element, html):
                event = self._extract_single_event(element, html)
                if event:
                    events.append(event)
        
        return events
    
    def _looks_like_event(self, element, html: str) -> bool:
        """Check if an element looks like it contains event information."""
        text = element.get_text().lower()
        
        # Check for event indicators
        event_indicators = ['date', 'time', 'ticket', 'event', 'show', 'concert']
        indicator_count = sum(1 for indicator in event_indicators if indicator in text)
        
        return indicator_count >= 2
    
    def _extract_single_event(self, element, html: str) -> Optional[ExtractResult]:
        """Extract a single event from an element."""
        try:
            # Extract basic information
            title = self._extract_text(element, self.custom_selectors.get('title', []))
            if not title:
                return None
            
            # Extract date/time
            date_text = self._extract_text(element, self.custom_selectors.get('date', []))
            if not date_text:
                return None
            
            starts_at_utc, ends_at_utc = self._parse_datetime(date_text)
            if not starts_at_utc:
                return None
            
            # Extract other information
            venue_name = self._extract_text(element, self.custom_selectors.get('venue', []))
            price_text = self._extract_text(element, self.custom_selectors.get('price', []))
            
            # Create ExtractResult
            return ExtractResult(
                site_slug=self.site_slug,
                venue_name=venue_name or "Unknown Venue",
                title=title,
                artist_name=None,  # Could be extracted separately
                starts_at_utc=starts_at_utc,
                ends_at_utc=ends_at_utc,
                tz_name="America/New_York",  # Default, could be detected
                doors_time_utc=None,
                price_min=None,  # Could parse from price_text
                price_max=None,
                currency="USD",
                ticket_url=None,
                age_restriction=None,
                is_cancelled=False,
                source_url=self.source_url,
                external_id=None,
                raw_data={
                    "extraction_method": "adaptive",
                    "venue_type": self.venue_type,
                    "date_text": date_text,
                    "price_text": price_text
                }
            )
            
        except Exception as e:
            logger.debug(f"Error extracting single event: {e}")
            return None
    
    def _extract_text(self, element, selectors: List[str]) -> Optional[str]:
        """Extract text using multiple selectors."""
        for selector in selectors:
            found = element.select_one(selector)
            if found:
                text = found.get_text(strip=True)
                if text:
                    return text
        
        # Fall back to element's own text
        return element.get_text(strip=True)
    
    def _parse_datetime(self, date_text: str) -> tuple[Optional[str], Optional[str]]:
        """Parse datetime using configured patterns."""
        # This would implement the date parsing logic
        # For now, return None to indicate parsing failure
        return None, None
    
    def _learn_successful_patterns(self, html: str, events: List[ExtractResult]):
        """Learn from successful extraction patterns."""
        # Store patterns that led to successful extraction
        # This could be used to improve future extractions
        pass
    
    def _learn_failed_patterns(self, html: str):
        """Learn from failed extraction attempts."""
        # Store patterns that led to failed extraction
        # This could be used to avoid similar patterns in the future
        pass
    
    def get_extraction_stats(self) -> Dict[str, Any]:
        """Get current extraction statistics."""
        return self.extraction_stats.copy()
