"""
Intelligent Source Discovery Engine

Automatically discovers venue calendars and event sources through:
- Search engine APIs
- Venue aggregator sites
- Local business directories
- Cross-reference analysis
"""
import asyncio
import re
import logging
from typing import List, Dict, Set, Optional, Tuple
from dataclasses import dataclass
from urllib.parse import urljoin, urlparse, parse_qs
import aiohttp
from bs4 import BeautifulSoup
import json
import time
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)


@dataclass
class DiscoveredSource:
    """Represents a discovered event source."""
    url: str
    name: str
    source_type: str  # 'venue', 'ticketing', 'aggregator', 'media', 'social'
    confidence_score: float  # 0.0 to 1.0
    venue_name: Optional[str] = None
    address: Optional[str] = None
    phone: Optional[str] = None
    description: Optional[str] = None
    last_updated: Optional[datetime] = None
    event_count: Optional[int] = None
    calendar_detected: bool = False
    requires_browser: bool = False
    rate_limit_rps: Optional[float] = None
    priority_score: float = 0.0 # Added for priority scoring


@dataclass
class DiscoveryResult:
    """Result of a discovery operation."""
    sources: List[DiscoveredSource]
    total_discovered: int
    discovery_method: str
    search_terms: List[str]
    execution_time: float


class SourceDiscoverer:
    """Intelligent source discovery engine."""
    
    def __init__(self, site_slug: str, city: str, state: str):
        self.site_slug = site_slug
        self.city = city
        self.state = state
        self.session: Optional[aiohttp.ClientSession] = None
        
        # Common event-related keywords
        self.event_keywords = [
            "live music", "concerts", "shows", "events", "calendar",
            "tickets", "performances", "gigs", "bands", "artists"
        ]
        
        # Calendar detection patterns
        self.calendar_patterns = [
            r'\b(?:january|february|march|april|may|june|july|august|september|october|november|december)\s+\d{1,2}',
            r'\b(?:mon|tue|wed|thu|fri|sat|sun)\s+\d{1,2}',
            r'\d{1,2}/\d{1,2}/\d{4}',
            r'\d{4}-\d{2}-\d{2}',
            r'\b(?:today|tomorrow|this week|next week)\b',
            r'\b(?:doors|show starts|performance)\b',
            r'\b(?:buy tickets|rsvp|get tickets)\b'
        ]
        
        # Known aggregator domains
        self.known_aggregators = {
            'eventbrite.com': 'ticketing',
            'ticketmaster.com': 'ticketing',
            'bandsintown.com': 'aggregator',
            'songkick.com': 'aggregator',
            'jambase.com': 'aggregator',
            'pollstar.com': 'aggregator',
            'seatgeek.com': 'ticketing',
            'stubhub.com': 'ticketing'
        }
        
        # Local business directories
        self.business_directories = [
            'yelp.com',
            'google.com/maps',
            'yellowpages.com',
            'chamberofcommerce.com'
        ]

        # Charleston venue patterns for priority scoring
        self.charleston_venue_patterns = {
            "musicfarm": {"name": "Music Farm", "keywords": ["music farm", "musicfarm"]},
            "pourhouse": {"name": "The Pour House", "keywords": ["pour house", "pourhouse"]},
            "charlestonmusichall": {"name": "Charleston Music Hall", "keywords": ["charleston music hall", "charlestonmusichall"]},
            "themillcharleston": {"name": "The Mill", "keywords": ["the mill", "themillcharleston"]},
            "acescharleston": {"name": "Aces", "keywords": ["aces", "acescharleston"]},
            "theroyalamerican": {"name": "The Royal American", "keywords": ["the royal american", "theroyalamerican"]}
        }
        
        # Blacklist for consistently failing sources
        self.blacklisted_sources = {
            'duckduckgo.com': 'Consistently times out and blocks automated requests',
            'html.duckduckgo.com': 'HTML search endpoint is unreliable',
            'google.com': 'Requires API key and has rate limits',
            'bing.com': 'Requires API key and has rate limits'
        }
    
    async def __aenter__(self):
        """Async context manager entry."""
        self.session = aiohttp.ClientSession(
            timeout=aiohttp.ClientTimeout(total=30),
            headers={
                'User-Agent': 'Mozilla/5.0 (compatible; MusicLiveBot/1.0; +https://musiclive.com/bot)'
            }
        )
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        if self.session:
            await self.session.close()
    
    async def discover_sources(self, max_sources: int = 50) -> DiscoveryResult:
        """Main discovery method that combines multiple discovery strategies."""
        start_time = time.time()
        all_sources: Set[str] = set()
        discovered_sources: List[DiscoveredSource] = []
        
        # Strategy 1: Direct venue discovery (highest priority)
        logger.info("Starting direct venue discovery...")
        direct_venue_sources = await self._discover_direct_venues(max_sources // 3)
        for source in direct_venue_sources:
            if source.url not in all_sources:
                all_sources.add(source.url)
                discovered_sources.append(source)
        
        # Strategy 2: Search engine discovery
        logger.info("Starting search engine discovery...")
        search_sources = await self._discover_via_search_engines(max_sources // 3)
        for source in search_sources:
            if source.url not in all_sources:
                all_sources.add(source.url)
                discovered_sources.append(source)
        
        # Strategy 3: Known aggregator discovery
        logger.info("Starting aggregator discovery...")
        aggregator_sources = await self._discover_via_aggregators(max_sources // 6)
        for source in aggregator_sources:
            if source.url not in all_sources:
                all_sources.add(source.url)
                discovered_sources.append(source)
        
        # Strategy 4: Cross-reference discovery
        logger.info("Starting cross-reference discovery...")
        cross_ref_sources = await self._discover_via_cross_references(discovered_sources, max_sources // 6)
        for source in cross_ref_sources:
            if source.url not in all_sources:
                all_sources.add(source.url)
                discovered_sources.append(source)
        
        # Calculate priority scores and sort
        for source in discovered_sources:
            source.priority_score = self._calculate_priority_score(source)
        
        # Sort by priority score first, then confidence score
        discovered_sources.sort(key=lambda x: (x.priority_score, x.confidence_score), reverse=True)
        
        execution_time = time.time() - start_time
        
        return DiscoveryResult(
            sources=discovered_sources[:max_sources],
            total_discovered=len(discovered_sources),
            discovery_method="multi_strategy",
            search_terms=[f"{self.city} live music", f"{self.city} concerts", f"{self.city} venues"],
            execution_time=execution_time
        )
    
    async def _discover_direct_venues(self, max_sources: int) -> List[DiscoveredSource]:
        """Discover direct venue websites for Charleston."""
        sources = []
        
        # Charleston-specific venue URLs to check directly
        charleston_venues = [
            "https://www.musicfarm.com",
            "https://www.pourhouse.com",
            "https://www.charlestonmusichall.com",
            "https://www.themillcharleston.com",
            "https://www.acescharleston.com",
            "https://www.theroyalamerican.com"
        ]
        
        for venue_url in charleston_venues:
            try:
                # Check if the venue has an events/calendar page
                calendar_urls = [
                    f"{venue_url}/events",
                    f"{venue_url}/calendar",
                    f"{venue_url}/shows",
                    f"{venue_url}/schedule",
                    f"{venue_url}/upcoming-events"
                ]
                
                for calendar_url in calendar_urls:
                    try:
                        source = await self._analyze_potential_source(calendar_url, "Charleston Venue")
                        if source and source.confidence_score > 0.5:
                            # Boost priority for direct venues
                            source.priority_score = 1.0
                            source.source_type = 'venue'
                            sources.append(source)
                            break  # Found a working calendar page for this venue
                            
                    except Exception as e:
                        logger.debug(f"Calendar page {calendar_url} not accessible: {e}")
                        continue
                        
                if len(sources) >= max_sources:
                    break
                    
            except Exception as e:
                logger.error(f"Error discovering venue {venue_url}: {e}")
                continue
        
        return sources
    
    def _calculate_priority_score(self, source: DiscoveredSource) -> float:
        """Calculate priority score for a discovered source."""
        base_score = source.confidence_score
        
        # Boost direct venues
        if source.source_type == 'venue':
            base_score += 0.3
        
        # Boost Charleston-specific venues
        if self.site_slug == 'charleston':
            for venue_info in self.charleston_venue_patterns.values():
                if venue_info['name'].lower() in source.name.lower():
                    base_score += 0.4
                    break
        
        # Boost sources with calendars
        if source.calendar_detected:
            base_score += 0.2
        
        # Boost sources with high event counts
        if source.event_count and source.event_count > 10:
            base_score += 0.1
        
        # Penalize aggregators slightly (we want them but prioritize venues)
        if source.source_type in ['aggregator', 'ticketing']:
            base_score -= 0.1
        
        return min(base_score, 1.0)  # Cap at 1.0
    
    async def _discover_via_search_engines(self, max_sources: int) -> List[DiscoveredSource]:
        """Discover sources using search engine APIs."""
        sources = []
        
        # Skip search engine discovery for now since DuckDuckGo is blacklisted
        # and we don't have API keys for Google/Bing
        logger.info("Skipping search engine discovery - all major engines are blacklisted or require API keys")
        
        # In the future, we could implement:
        # - Google Custom Search API (requires API key)
        # - Bing Web Search API (requires API key)
        # - Alternative search engines that are more bot-friendly
        
        return sources
    
    async def _discover_via_aggregators(self, max_sources: int) -> List[DiscoveredSource]:
        """Discover sources by scraping known aggregator sites."""
        sources = []
        
        # Search aggregators for the specific city
        aggregator_searches = [
            f"https://www.eventbrite.com/d/{self.city}--{self.state}/live-music/",
            f"https://www.bandsintown.com/?location={self.city}%2C{self.state}",
            f"https://www.songkick.com/search?query={self.city}%2C{self.state}",
            f"https://www.jambase.com/place/{self.city}-{self.state}"
        ]
        
        for url in aggregator_searches:
            try:
                source = await self._analyze_potential_source(url, f"{self.city} Events")
                if source:
                    sources.append(source)
                    
                    if len(sources) >= max_sources:
                        break
                        
            except Exception as e:
                logger.error(f"Error analyzing aggregator {url}: {e}")
                continue
        
        return sources
    
    async def _discover_via_cross_references(self, existing_sources: List[DiscoveredSource], max_sources: int) -> List[DiscoveredSource]:
        """Discover new sources by analyzing existing sources for references."""
        sources = []
        discovered_urls = set()
        
        for source in existing_sources[:10]:  # Limit to avoid too many requests
            try:
                # Extract links from the source page
                links = await self._extract_event_related_links(source.url)
                
                for link in links:
                    if link not in discovered_urls and len(sources) < max_sources:
                        discovered_urls.add(link)
                        
                        # Quick analysis to see if it's worth investigating
                        if await self._is_potential_event_source(link):
                            source_info = await self._analyze_potential_source(link, "Cross-referenced")
                            if source_info and source_info.confidence_score > 0.4:
                                sources.append(source_info)
                                
            except Exception as e:
                logger.error(f"Error in cross-reference discovery for {source.url}: {e}")
                continue
        
        return sources
    
    async def _search_duckduckgo(self, query: str, max_results: int = 10) -> List[Dict[str, str]]:
        """Search using DuckDuckGo (no API key required)."""
        try:
            # DuckDuckGo search URL
            search_url = "https://html.duckduckgo.com/html/"
            params = {
                'q': query,
                'kl': 'us-en'
            }
            
            async with self.session.get(search_url, params=params) as response:
                if response.status == 200:
                    html = await response.text()
                    soup = BeautifulSoup(html, 'html.parser')
                    
                    results = []
                    # DuckDuckGo result links
                    for link in soup.find_all('a', class_='result__a'):
                        if len(results) >= max_results:
                            break
                        
                        href = link.get('href')
                        if href and href.startswith('http'):
                            results.append({
                                'url': href,
                                'title': link.get_text(strip=True)
                            })
                    
                    return results
                    
        except Exception as e:
            logger.error(f"Error searching DuckDuckGo: {e}")
        
        return []
    
    async def _analyze_potential_source(self, url: str, title: str) -> Optional[DiscoveredSource]:
        """Analyze a potential source to determine if it's an event source."""
        # Check if source is blacklisted
        if self._is_source_blacklisted(url):
            reason = self._get_blacklist_reason(url)
            logger.info(f"Skipping blacklisted source {url}: {reason}")
            return None
        
        try:
            # Quick check if URL is accessible
            async with self.session.get(url, timeout=10) as response:
                if response.status != 200:
                    return None
                
                html = await response.text()
                
                # Analyze the page content
                analysis = await self._analyze_page_content(url, html, title)
                
                return analysis
                
        except Exception as e:
            logger.debug(f"Error analyzing {url}: {e}")
            return None
    
    async def _analyze_page_content(self, url: str, html: str, title: str) -> DiscoveredSource:
        """Analyze page content to determine source type and confidence."""
        soup = BeautifulSoup(html, 'html.parser')
        
        # Initialize analysis
        source_type = 'unknown'
        confidence_score = 0.0
        venue_name = None
        address = None
        phone = None
        description = None
        event_count = 0
        calendar_detected = False
        requires_browser = False
        
        # Check for calendar indicators
        calendar_score = self._detect_calendar_indicators(html)
        if calendar_score > 0.5:
            calendar_detected = True
            confidence_score += 0.3
        
        # Check for event-related content
        event_score = self._detect_event_content(html)
        confidence_score += event_score * 0.4
        
        # Determine source type
        domain = urlparse(url).netloc.lower()
        
        if any(agg in domain for agg in self.known_aggregators):
            source_type = self.known_aggregators.get(domain, 'aggregator')
            confidence_score += 0.2
        elif 'venue' in title.lower() or 'club' in title.lower() or 'theater' in title.lower():
            source_type = 'venue'
            confidence_score += 0.2
        elif 'ticket' in title.lower() or 'event' in title.lower():
            source_type = 'ticketing'
            confidence_score += 0.2
        elif 'bar' in title.lower() or 'restaurant' in title.lower():
            source_type = 'social'
            confidence_score += 0.1
        
        # Extract venue information
        venue_name = self._extract_venue_name(soup, title)
        address = self._extract_address(soup)
        phone = self._extract_phone(soup)
        description = self._extract_description(soup)
        
        # Count potential events
        event_count = self._count_potential_events(html)
        if event_count > 0:
            confidence_score += min(event_count * 0.05, 0.3)
        
        # Check if JavaScript is required
        if self._requires_javascript(html):
            requires_browser = True
            confidence_score -= 0.1  # Slightly lower confidence for JS-heavy sites
        
        # Normalize confidence score
        confidence_score = min(max(confidence_score, 0.0), 1.0)
        
        return DiscoveredSource(
            url=url,
            name=title or venue_name or domain,
            source_type=source_type,
            confidence_score=confidence_score,
            venue_name=venue_name,
            address=address,
            phone=phone,
            description=description,
            event_count=event_count,
            calendar_detected=calendar_detected,
            requires_browser=requires_browser,
            rate_limit_rps=1.0  # Conservative default
        )
    
    def _detect_calendar_indicators(self, html: str) -> float:
        """Detect calendar indicators in HTML content."""
        score = 0.0
        
        for pattern in self.calendar_patterns:
            matches = len(re.findall(pattern, html, re.IGNORECASE))
            if matches > 0:
                score += min(matches * 0.1, 0.5)
        
        # Check for calendar-specific HTML elements
        calendar_elements = [
            'calendar', 'datepicker', 'month', 'week', 'day',
            'event-calendar', 'schedule', 'upcoming'
        ]
        
        for element in calendar_elements:
            if element in html.lower():
                score += 0.1
        
        return min(score, 1.0)
    
    def _detect_event_content(self, html: str) -> float:
        """Detect event-related content in HTML."""
        score = 0.0
        
        for keyword in self.event_keywords:
            matches = len(re.findall(rf'\b{re.escape(keyword)}\b', html, re.IGNORECASE))
            if matches > 0:
                score += min(matches * 0.05, 0.3)
        
        return min(score, 1.0)
    
    def _extract_venue_name(self, soup: BeautifulSoup, title: str) -> Optional[str]:
        """Extract venue name from page content."""
        # Try common selectors for venue names
        selectors = [
            'h1', 'h2', '.venue-name', '.business-name', '[class*="venue"]',
            '[class*="business"]', '[class*="name"]'
        ]
        
        for selector in selectors:
            element = soup.select_one(selector)
            if element:
                text = element.get_text(strip=True)
                if text and len(text) < 100:  # Reasonable venue name length
                    return text
        
        # Fall back to title if it looks like a venue name
        if any(word in title.lower() for word in ['venue', 'club', 'theater', 'bar', 'restaurant']):
            return title
        
        return None
    
    def _extract_address(self, soup: BeautifulSoup) -> Optional[str]:
        """Extract address information from page content."""
        # Look for address patterns
        address_patterns = [
            r'\d+\s+[A-Za-z\s]+(?:Street|St|Avenue|Ave|Road|Rd|Boulevard|Blvd)',
            r'[A-Za-z\s]+,?\s+[A-Z]{2}\s+\d{5}',
            r'[A-Za-z\s]+,\s+[A-Za-z\s]+,\s+[A-Z]{2}'
        ]
        
        text = soup.get_text()
        for pattern in address_patterns:
            match = re.search(pattern, text)
            if match:
                return match.group(0)
        
        return None
    
    def _extract_phone(self, soup: BeautifulSoup) -> Optional[str]:
        """Extract phone number from page content."""
        phone_pattern = r'\(?\d{3}\)?[\s.-]?\d{3}[\s.-]?\d{4}'
        text = soup.get_text()
        
        match = re.search(phone_pattern, text)
        if match:
            return match.group(0)
        
        return None
    
    def _extract_description(self, soup: BeautifulSoup) -> Optional[str]:
        """Extract description from page content."""
        # Look for meta description
        meta_desc = soup.find('meta', attrs={'name': 'description'})
        if meta_desc and meta_desc.get('content'):
            return meta_desc['content'][:200]  # Limit length
        
        # Look for first paragraph
        first_p = soup.find('p')
        if first_p:
            text = first_p.get_text(strip=True)
            if text and len(text) > 20:
                return text[:200]
        
        return None
    
    def _count_potential_events(self, html: str) -> int:
        """Count potential events on the page."""
        # Look for repeated structures that might be events
        event_indicators = [
            'event-item', 'event-list', 'show-item', 'concert-item',
            'ticket-item', 'performance-item'
        ]
        
        count = 0
        for indicator in event_indicators:
            count += html.lower().count(indicator)
        
        # Also count date patterns as potential events
        date_pattern = r'\b(?:jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec)\s+\d{1,2}'
        date_matches = len(re.findall(date_pattern, html, re.IGNORECASE))
        count += date_matches
        
        return count
    
    def _requires_javascript(self, html: str) -> bool:
        """Check if the page requires JavaScript for content."""
        js_indicators = [
            'react', 'vue', 'angular', 'spa', 'single-page',
            'data-react', 'data-vue', 'ng-', 'v-'
        ]
        
        for indicator in js_indicators:
            if indicator in html.lower():
                return True
        
        return False
    
    async def _extract_event_related_links(self, url: str) -> List[str]:
        """Extract event-related links from a page."""
        try:
            async with self.session.get(url, timeout=10) as response:
                if response.status != 200:
                    return []
                
                html = await response.text()
                soup = BeautifulSoup(html, 'html.parser')
                
                links = []
                for link in soup.find_all('a', href=True):
                    href = link['href']
                    
                    # Convert relative URLs to absolute
                    if href.startswith('/'):
                        href = urljoin(url, href)
                    elif not href.startswith('http'):
                        continue
                    
                    # Filter for potentially relevant links
                    if self._is_relevant_link(href, link.get_text()):
                        links.append(href)
                
                return links[:20]  # Limit to avoid too many links
                
        except Exception as e:
            logger.debug(f"Error extracting links from {url}: {e}")
            return []
    
    def _is_relevant_link(self, url: str, text: str) -> bool:
        """Check if a link is relevant to event discovery."""
        relevant_keywords = [
            'events', 'calendar', 'shows', 'concerts', 'tickets',
            'venue', 'club', 'theater', 'bar', 'restaurant'
        ]
        
        url_lower = url.lower()
        text_lower = text.lower()
        
        # Check if URL or text contains relevant keywords
        for keyword in relevant_keywords:
            if keyword in url_lower or keyword in text_lower:
                return True
        
        return False
    
    async def _is_potential_event_source(self, url: str) -> bool:
        """Quick check if a URL might be an event source."""
        try:
            # Just check the response status and basic content
            async with self.session.head(url, timeout=5) as response:
                if response.status != 200:
                    return False
                
                # Check content type
                content_type = response.headers.get('content-type', '')
                if 'text/html' not in content_type:
                    return False
                
                return True
                
        except Exception:
            return False
    
    def _is_source_blacklisted(self, url: str) -> bool:
        """Check if a source URL is in the blacklist."""
        try:
            parsed = urlparse(url)
            domain = parsed.netloc.lower()
            return domain in self.blacklisted_sources
        except Exception:
            return False
    
    def _get_blacklist_reason(self, url: str) -> Optional[str]:
        """Get the reason why a source is blacklisted."""
        try:
            parsed = urlparse(url)
            domain = parsed.netloc.lower()
            return self.blacklisted_sources.get(domain)
        except Exception:
            return None


async def discover_sources_for_site(site_slug: str, city: str, state: str, max_sources: int = 50) -> DiscoveryResult:
    """Convenience function to discover sources for a site."""
    async with SourceDiscoverer(site_slug, city, state) as discoverer:
        return await discoverer.discover_sources(max_sources)
