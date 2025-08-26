"""
Intelligent Music Event Crawler

Automatically discovers, analyzes, and crawls event sources without manual configuration.
Uses machine learning and pattern recognition to adapt to different venue types.
"""
import asyncio
import logging
import time
from typing import List, Dict, Any, Optional, Set
from dataclasses import dataclass
from datetime import datetime, timedelta
import json
import os

from .discovery.source_discoverer import SourceDiscoverer, DiscoveredSource, DiscoveryResult
from .extractors.factory import ExtractorFactory, ExtractorMatch
from .extractors.base import ExtractResult
from .crawlers.factory import CrawlerFactory, CrawlerType
from .artist_researcher import ArtistResearcher
from db.persistence import (
    get_connection, ensure_site, ensure_source, upsert_venue, 
    insert_event_instance, upsert_event_source_link
)

logger = logging.getLogger(__name__)


@dataclass
class CrawlResult:
    """Result of a crawling operation."""
    source_url: str
    events_found: int
    events_extracted: int
    extraction_confidence: float
    extractor_used: str
    crawl_duration: float
    errors: List[str]
    success: bool


@dataclass
class CrawlSession:
    """Represents a complete crawling session."""
    site_slug: str
    city: str
    state: str
    start_time: datetime
    end_time: Optional[datetime] = None
    sources_discovered: int = 0
    sources_crawled: int = 0
    total_events_found: int = 0
    successful_crawls: int = 0
    failed_crawls: int = 0
    crawl_results: List[CrawlResult] = None
    
    def __post_init__(self):
        if self.crawl_results is None:
            self.crawl_results = []


class IntelligentCrawler:
    """Intelligent crawler that automatically discovers and crawls event sources."""
    
    def __init__(self, site_slug: str, city: str, state: str):
        self.site_slug = site_slug
        self.city = city
        self.state = state
        self.discoverer: Optional[SourceDiscoverer] = None
        self.extractor_factory = ExtractorFactory()
        
        # Crawling configuration
        self.max_sources_to_discover = 50
        self.max_sources_to_crawl = 20
        self.min_confidence_threshold = 0.4
        self.rate_limit_delay = 1.0  # seconds between requests
        
        # Session tracking
        self.current_session: Optional[CrawlSession] = None
        
        # Learning and adaptation
        self.successful_patterns: Dict[str, Any] = {}
        self.failed_patterns: Dict[str, Any] = {}
        self.venue_extractor_mapping: Dict[str, str] = {}
        
        # Artist research
        self.artist_researcher: Optional[ArtistResearcher] = None
    
    async def __aenter__(self):
        """Async context manager entry."""
        self.discoverer = SourceDiscoverer(self.site_slug, self.city, self.state)
        await self.discoverer.__aenter__()
        
        # Initialize artist researcher
        self.artist_researcher = ArtistResearcher()
        await self.artist_researcher.__aenter__()
        
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        if self.discoverer:
            await self.discoverer.__aexit__(exc_type, exc_val, exc_tb)
        if self.artist_researcher:
            await self.artist_researcher.__aexit__(exc_type, exc_val, exc_tb)
    
    async def run_full_crawl(self) -> CrawlSession:
        """Run a complete crawling session from discovery to extraction."""
        self.current_session = CrawlSession(
            site_slug=self.site_slug,
            city=self.city,
            state=self.state,
            start_time=datetime.utcnow()
        )
        
        try:
            logger.info(f"Starting intelligent crawl for {self.city}, {self.state}")
            
            # Phase 1: Discover sources
            logger.info("Phase 1: Discovering event sources...")
            discovery_result = await self.discoverer.discover_sources(self.max_sources_to_discover)
            self.current_session.sources_discovered = len(discovery_result.sources)
            
            logger.info(f"Discovered {len(discovery_result.sources)} potential sources")
            
            # Store discovered sources in database for future reference
            logger.info("Storing discovered sources in database...")
            await self._store_discovered_sources(discovery_result.sources)
            
            # Phase 2: Filter and prioritize sources
            logger.info("Phase 2: Filtering and prioritizing sources...")
            prioritized_sources = self._prioritize_sources(discovery_result.sources)
            
            # Phase 3: Crawl sources
            logger.info("Phase 3: Crawling sources...")
            await self._crawl_sources(prioritized_sources[:self.max_sources_to_crawl])
            
            # Phase 4: Store results in database
            logger.info("Phase 4: Storing results in database...")
            await self._store_crawl_results()
            
            # Phase 5: Learn and adapt
            logger.info("Phase 5: Learning and adapting...")
            self._learn_from_session()
            
            self.current_session.end_time = datetime.utcnow()
            self.current_session.successful_crawls = len([r for r in self.current_session.crawl_results if r.success])
            self.current_session.failed_crawls = len([r for r in self.current_session.crawl_results if not r.success])
            
            logger.info(f"Crawl session completed. "
                       f"Sources: {self.current_session.sources_crawled}, "
                       f"Events: {self.current_session.total_events_found}, "
                       f"Success Rate: {self.current_session.successful_crawls}/{self.current_session.sources_crawled}")
            
            return self.current_session
            
        except Exception as e:
            logger.error(f"Error during crawl session: {e}")
            if self.current_session:
                self.current_session.end_time = datetime.utcnow()
            raise
    
    def _prioritize_sources(self, sources: List[DiscoveredSource]) -> List[DiscoveredSource]:
        """Prioritize sources based on confidence and venue type."""
        # Sort by confidence score first
        sources.sort(key=lambda x: x.confidence_score, reverse=True)
        
        # Apply business logic for prioritization
        prioritized = []
        
        # High priority: Venues with high confidence and calendar detection
        high_priority = [s for s in sources if s.confidence_score > 0.7 and s.calendar_detected]
        prioritized.extend(high_priority)
        
        # Medium priority: Known aggregators and ticketing platforms
        medium_priority = [s for s in sources if s.source_type in ['ticketing', 'aggregator'] and s.confidence_score > 0.5]
        prioritized.extend(medium_priority)
        
        # Lower priority: Other sources above threshold
        other_sources = [s for s in sources if s not in prioritized and s.confidence_score > self.min_confidence_threshold]
        prioritized.extend(other_sources)
        
        # Remove duplicates while preserving order
        seen = set()
        unique_sources = []
        for source in prioritized:
            if source.url not in seen:
                seen.add(source.url)
                unique_sources.append(source)
        
        return unique_sources
    
    async def _crawl_sources(self, sources: List[DiscoveredSource]):
        """Crawl the prioritized sources."""
        for i, source in enumerate(sources):
            try:
                logger.info(f"Crawling source {i+1}/{len(sources)}: {source.name} ({source.url})")
                
                crawl_result = await self._crawl_single_source(source)
                self.current_session.crawl_results.append(crawl_result)
                
                if crawl_result.success:
                    self.current_session.total_events_found += crawl_result.events_extracted
                
                self.current_session.sources_crawled += 1
                
                # Rate limiting
                if i < len(sources) - 1:  # Don't delay after the last source
                    await asyncio.sleep(self.rate_limit_delay)
                
            except Exception as e:
                logger.error(f"Error crawling source {source.url}: {e}")
                # Create a failed crawl result
                failed_result = CrawlResult(
                    source_url=source.url,
                    events_found=0,
                    events_extracted=0,
                    extraction_confidence=0.0,
                    extractor_used="none",
                    crawl_duration=0.0,
                    errors=[str(e)],
                    success=False
                )
                self.current_session.crawl_results.append(failed_result)
                self.current_session.sources_crawled += 1
    
    async def _crawl_single_source(self, source: DiscoveredSource) -> CrawlResult:
        """Crawl a single source and extract events."""
        start_time = time.time()
        errors = []
        
        try:
            # Download the page content
            async with self.discoverer.session.get(source.url, timeout=30) as response:
                if response.status != 200:
                    errors.append(f"HTTP {response.status}: {response.reason}")
                    raise Exception(f"Failed to fetch {source.url}: HTTP {response.status}")
                
                html_content = await response.text()
            
            # Analyze the page and choose extractor
            extractor_match = self.extractor_factory.analyze_source(
                source.url, html_content, {
                    'venue_name': source.venue_name,
                    'source_type': source.source_type,
                    'calendar_detected': source.calendar_detected,
                    'requires_browser': source.requires_browser
                }
            )
            
            # Create and use the extractor
            extractor = self.extractor_factory.create_extractor(
                extractor_match, self.site_slug, source.url
            )
            
            # Extract events
            events = extractor.parse(html_content)
            
            # Research artists from events
            if events and self.artist_researcher:
                await self._research_artists_from_events(events)
            
            # Store events in database
            stored_events = await self._store_events_from_source(source, events)
            
            crawl_duration = time.time() - start_time
            
            return CrawlResult(
                source_url=source.url,
                events_found=len(events),
                events_extracted=len(stored_events),
                extraction_confidence=extractor_match.confidence_score,
                extractor_used=extractor_match.extractor_class.__name__,
                crawl_duration=crawl_duration,
                errors=errors,
                success=True
            )
            
        except Exception as e:
            crawl_duration = time.time() - start_time
            errors.append(str(e))
            
            return CrawlResult(
                source_url=source.url,
                events_found=0,
                events_extracted=0,
                extraction_confidence=0.0,
                extractor_used="none",
                crawl_duration=crawl_duration,
                errors=errors,
                success=False
            )
    
    async def _store_events_from_source(self, source: DiscoveredSource, events: List[ExtractResult]) -> List[int]:
        """Store extracted events in the database."""
        if not events:
            return []
        
        stored_event_ids = []
        
        try:
            conn = get_connection()
            
            with conn.cursor() as cur:
                # Start transaction
                cur.execute("BEGIN")
                
                try:
                    # Ensure site and source exist
                    site_id = ensure_site(conn, self.site_slug)
                    source_id = ensure_source(
                        conn, site_id, source.name, source.url,
                        requires_browser=source.requires_browser,
                        rate_limit_rps=source.rate_limit_rps
                    )
                    
                    # Create ingest run
                    cur.execute(
                        """
                        INSERT INTO ingest_run (source_id, started_at, status)
                        VALUES (%s, now(), 'running')
                        RETURNING id
                        """,
                        (source_id,)
                    )
                    ingest_run_id = cur.fetchone()[0]
                    
                    # Process each event
                    for event in events:
                        try:
                            # Upsert venue
                            venue_id = upsert_venue(
                                conn, site_id, event.venue_name,
                                tz_name=event.tz_name
                            )
                            
                            # Parse datetime strings to datetime objects
                            from datetime import datetime
                            starts_at = datetime.fromisoformat(event.starts_at_utc.replace('Z', '+00:00'))
                            ends_at = None
                            if event.ends_at_utc:
                                ends_at = datetime.fromisoformat(event.ends_at_utc.replace('Z', '+00:00'))
                            
                            # Insert event instance
                            event_id = insert_event_instance(
                                conn, site_id, venue_id,
                                title=event.title,
                                description=None,
                                artist_name=event.artist_name,
                                starts_at_utc=starts_at,
                                ends_at_utc=ends_at,
                                tz_name=event.tz_name,
                                doors_time_utc=None,
                                price_min=event.price_min,
                                price_max=event.price_max,
                                currency=event.currency,
                                ticket_url=event.ticket_url,
                                age_restriction=event.age_restriction,
                                is_cancelled=event.is_cancelled,
                                source_created_at=None,
                                source_updated_at=None,
                            )
                            
                            # Upsert event source link
                            link_id = upsert_event_source_link(
                                conn, event_id, source_id, ingest_run_id,
                                external_id=event.external_id, 
                                source_url=event.source_url, 
                                raw_data=event.raw_data
                            )
                            
                            stored_event_ids.append(event_id)
                            
                        except Exception as e:
                            logger.error(f"Error storing event {event.title}: {e}")
                            continue
                    
                    # Complete ingest run
                    cur.execute(
                        "UPDATE ingest_run SET status = 'completed', finished_at = now() WHERE id = %s",
                        (ingest_run_id,)
                    )
                    
                    # Commit transaction
                    cur.execute("COMMIT")
                    
                except Exception as e:
                    # Rollback on error
                    cur.execute("ROLLBACK")
                    raise
                    
        except Exception as e:
            logger.error(f"Error storing events from source {source.url}: {e}")
            raise
        finally:
            if 'conn' in locals():
                conn.close()
        
        return stored_event_ids
    
    async def _research_artists_from_events(self, events: List[ExtractResult]):
        """Research artists discovered from events."""
        try:
            # Extract unique artist names from events
            artist_names = []
            event_contexts = []
            
            for event in events:
                if event.artist_name and event.artist_name not in artist_names:
                    artist_names.append(event.artist_name)
                    event_contexts.append({
                        'venue_name': event.venue_name,
                        'title': event.title,
                        'source_url': event.source_url
                    })
            
            if not artist_names:
                return
            
            logger.info(f"🎵 Researching {len(artist_names)} artists from events")
            
            # Research artists in parallel
            artist_infos = await self.artist_researcher.batch_research_artists(artist_names, event_contexts)
            
            # Store artist information in database
            await self._store_artist_information(artist_infos)
            
            logger.info(f"✅ Completed research for {len(artist_infos)} artists")
            
        except Exception as e:
            logger.error(f"Error researching artists: {e}")
    
    async def _store_artist_information(self, artist_infos: List[Any]):
        """Store artist information in the database."""
        try:
            conn = get_connection()
            
            with conn.cursor() as cur:
                # Start transaction
                cur.execute("BEGIN")
                
                try:
                    site_id = ensure_site(conn, self.site_slug)
                    
                    for artist_info in artist_infos:
                        try:
                            # Insert or update artist
                            cur.execute(
                                """
                                INSERT INTO artist (site_id, name, bio, genre_tags, hometown, 
                                                   active_years, official_website, social_media, 
                                                   primary_photo_url, confidence_score, 
                                                   research_status, discovered_at, last_researched_at)
                                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                                ON CONFLICT (site_id, name) 
                                DO UPDATE SET
                                    bio = EXCLUDED.bio,
                                    genre_tags = EXCLUDED.genre_tags,
                                    hometown = EXCLUDED.hometown,
                                    active_years = EXCLUDED.active_years,
                                    official_website = EXCLUDED.official_website,
                                    social_media = EXCLUDED.social_media,
                                    primary_photo_url = EXCLUDED.primary_photo_url,
                                    confidence_score = EXCLUDED.confidence_score,
                                    research_status = EXCLUDED.research_status,
                                    last_researched_at = EXCLUDED.last_researched_at
                                RETURNING id
                                """,
                                (site_id, artist_info.name, artist_info.bio, artist_info.genre_tags,
                                 artist_info.hometown, artist_info.active_years, artist_info.official_website,
                                 json.dumps(artist_info.social_media), artist_info.primary_photo_url,
                                 artist_info.confidence_score, artist_info.research_status,
                                 artist_info.discovered_at, artist_info.last_researched_at)
                            )
                            
                            artist_id = cur.fetchone()[0]
                            logger.info(f"💾 Stored artist: {artist_info.name} (ID: {artist_id})")
                            
                        except Exception as e:
                            logger.error(f"Error storing artist {artist_info.name}: {e}")
                            continue
                    
                    # Commit transaction
                    cur.execute("COMMIT")
                    
                except Exception as e:
                    # Rollback on error
                    cur.execute("ROLLBACK")
                    raise
                    
        except Exception as e:
            logger.error(f"Error storing artist information: {e}")
            raise
        finally:
            if 'conn' in locals():
                conn.close()
    
    async def _store_discovered_sources(self, sources: List[DiscoveredSource]):
        """Store discovered sources in the database."""
        if not sources:
            return
        
        try:
            conn = get_connection()
            
            with conn.cursor() as cur:
                # Start transaction
                cur.execute("BEGIN")
                
                try:
                    site_id = ensure_site(conn, self.site_slug)
                    
                    for source in sources:
                        try:
                            # Upsert source
                            source_id = ensure_source(
                                conn, site_id, source.name, source.url,
                                requires_browser=source.requires_browser,
                                rate_limit_rps=source.rate_limit_rps
                            )
                            logger.info(f"Stored source: {source.name} ({source.url})")
                        except Exception as e:
                            logger.error(f"Error storing source {source.url}: {e}")
                            continue
                    
                    # Commit transaction
                    cur.execute("COMMIT")
                    
                except Exception as e:
                    # Rollback on error
                    cur.execute("ROLLBACK")
                    raise
                    
        except Exception as e:
            logger.error(f"Error storing discovered sources: {e}")
            raise
        finally:
            if 'conn' in locals():
                conn.close()
    
    async def _store_crawl_results(self):
        """Store crawl session results in database for analysis."""
        # This could store crawl statistics, learning data, etc.
        # For now, we'll just log the results
        pass
    
    def _learn_from_session(self):
        """Learn from the crawl session to improve future crawls."""
        if not self.current_session:
            return
        
        # Analyze successful vs failed crawls
        successful_results = [r for r in self.current_session.crawl_results if r.success]
        failed_results = [r for r in self.current_session.crawl_results if not r.success]
        
        # Learn from successful patterns
        for result in successful_results:
            if result.extractor_used not in self.successful_patterns:
                self.successful_patterns[result.extractor_used] = []
            
            self.successful_patterns[result.extractor_used].append({
                'confidence': result.extraction_confidence,
                'events_found': result.events_found,
                'events_extracted': result.events_extracted,
                'duration': result.crawl_duration
            })
        
        # Learn from failed patterns
        for result in failed_results:
            if result.extractor_used not in self.failed_patterns:
                self.failed_patterns[result.extractor_used] = []
            
            self.failed_patterns[result.extractor_used].extend(result.errors)
        
        # Update venue-extractor mapping based on success rates
        for result in self.current_session.crawl_results:
            if result.success and result.events_extracted > 0:
                # This extractor worked well for this source
                domain = self._extract_domain(result.source_url)
                if domain:
                    self.venue_extractor_mapping[domain] = result.extractor_used
        
        logger.info(f"Learning complete. "
                   f"Successful patterns: {len(self.successful_patterns)}, "
                   f"Failed patterns: {len(self.failed_patterns)}, "
                   f"Venue mappings: {len(self.venue_extractor_mapping)}")
    
    def _extract_domain(self, url: str) -> Optional[str]:
        """Extract domain from URL."""
        from urllib.parse import urlparse
        try:
            parsed = urlparse(url)
            return parsed.netloc.lower()
        except Exception:
            return None
    
    def get_crawl_statistics(self) -> Dict[str, Any]:
        """Get statistics about the current crawl session."""
        if not self.current_session:
            return {}
        
        session = self.current_session
        duration = (session.end_time or datetime.utcnow()) - session.start_time
        
        return {
            'site_slug': session.site_slug,
            'city': session.city,
            'state': session.state,
            'start_time': session.start_time.isoformat(),
            'end_time': session.end_time.isoformat() if session.end_time else None,
            'duration_seconds': duration.total_seconds(),
            'sources_discovered': session.sources_discovered,
            'sources_crawled': session.sources_crawled,
            'total_events_found': session.total_events_found,
            'successful_crawls': session.successful_crawls,
            'failed_crawls': session.failed_crawls,
            'success_rate': session.successful_crawls / session.sources_crawled if session.sources_crawled > 0 else 0,
            'events_per_source': session.total_events_found / session.successful_crawls if session.successful_crawls > 0 else 0,
            'learning_data': {
                'successful_patterns': len(self.successful_patterns),
                'failed_patterns': len(self.failed_patterns),
                'venue_mappings': len(self.venue_extractor_mapping)
            }
        }


async def run_intelligent_crawl(site_slug: str, city: str, state: str) -> CrawlSession:
    """Convenience function to run an intelligent crawl."""
    async with IntelligentCrawler(site_slug, city, state) as crawler:
        return await crawler.run_full_crawl()


async def discover_and_crawl_sources(site_slug: str, city: str, state: str, max_sources: int = 20) -> Dict[str, Any]:
    """Discover sources and crawl them in one operation."""
    # First discover sources
    async with SourceDiscoverer(site_slug, city, state) as discoverer:
        discovery_result = await discoverer.discover_sources(max_sources * 2)  # Discover more than we'll crawl
    
    # Then crawl the best sources
    async with IntelligentCrawler(site_slug, city, state) as crawler:
        crawler.max_sources_to_crawl = max_sources
        crawl_session = await crawler.run_full_crawl()
    
    return {
        'discovery': discovery_result,
        'crawl': crawl_session,
        'statistics': crawler.get_crawl_statistics()
    }
