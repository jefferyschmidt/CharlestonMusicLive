"""
Artist Research System

Automatically discovers artists from events and researches their information
from official websites and social media.
"""
import asyncio
import logging
import re
from typing import List, Dict, Any, Optional
from dataclasses import dataclass
from datetime import datetime
import aiohttp
from selectolax.parser import HTMLParser
from urllib.parse import urljoin, urlparse

logger = logging.getLogger(__name__)


@dataclass
class ArtistInfo:
    """Represents discovered artist information."""
    name: str
    bio: Optional[str] = None
    genre_tags: List[str] = None
    hometown: Optional[str] = None
    active_years: Optional[str] = None
    official_website: Optional[str] = None
    social_media: Dict[str, str] = None
    primary_photo_url: Optional[str] = None
    confidence_score: float = 0.0
    research_status: str = 'pending'  # pending, in_progress, completed, failed
    discovered_at: datetime = None
    last_researched_at: datetime = None
    
    def __post_init__(self):
        if self.genre_tags is None:
            self.genre_tags = []
        if self.social_media is None:
            self.social_media = {}
        if self.discovered_at is None:
            self.discovered_at = datetime.now()


class ArtistResearcher:
    """Researches artists discovered from events."""
    
    def __init__(self):
        self.session: Optional[aiohttp.ClientSession] = None
        self.research_cache = {}
        
        # Common social media platforms
        self.social_platforms = {
            'facebook.com': 'facebook',
            'twitter.com': 'twitter',
            'instagram.com': 'instagram',
            'youtube.com': 'youtube',
            'spotify.com': 'spotify',
            'soundcloud.com': 'soundcloud',
            'bandcamp.com': 'bandcamp',
            'tiktok.com': 'tiktok'
        }
        
        # Genre keywords for classification
        self.genre_keywords = {
            'rock': ['rock', 'metal', 'punk', 'grunge', 'indie'],
            'pop': ['pop', 'pop-rock', 'dance-pop', 'synth-pop'],
            'country': ['country', 'folk', 'bluegrass', 'americana'],
            'jazz': ['jazz', 'blues', 'swing', 'bebop'],
            'electronic': ['electronic', 'edm', 'techno', 'house', 'dubstep'],
            'hip_hop': ['hip hop', 'rap', 'trap', 'r&b'],
            'classical': ['classical', 'orchestral', 'chamber', 'symphony']
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
    
    async def research_artist(self, artist_name: str, event_context: Dict[str, Any] = None) -> ArtistInfo:
        """Research an artist and return comprehensive information."""
        try:
            logger.info(f"🔍 Researching artist: {artist_name}")
            
            # Check cache first
            if artist_name in self.research_cache:
                logger.info(f"📋 Found {artist_name} in cache")
                return self.research_cache[artist_name]
            
            # Create initial artist info
            artist_info = ArtistInfo(name=artist_name)
            
            # Strategy 1: Search for official website
            official_website = await self._find_official_website(artist_name)
            if official_website:
                artist_info.official_website = official_website
                artist_info.confidence_score += 0.3
                
                # Research the official website
                website_info = await self._research_official_website(official_website)
                artist_info.bio = website_info.get('bio')
                artist_info.hometown = website_info.get('hometown')
                artist_info.active_years = website_info.get('active_years')
                artist_info.primary_photo_url = website_info.get('primary_photo')
                artist_info.confidence_score += 0.2
            
            # Strategy 2: Search for social media profiles
            social_media = await self._find_social_media(artist_name)
            if social_media:
                artist_info.social_media.update(social_media)
                artist_info.confidence_score += 0.2
            
            # Strategy 3: Classify genre based on context and research
            genre_tags = await self._classify_genre(artist_name, event_context, artist_info)
            if genre_tags:
                artist_info.genre_tags = genre_tags
                artist_info.confidence_score += 0.1
            
            # Cap confidence score
            artist_info.confidence_score = min(artist_info.confidence_score, 1.0)
            artist_info.research_status = 'completed'
            artist_info.last_researched_at = datetime.now()
            
            # Cache the result
            self.research_cache[artist_name] = artist_info
            
            logger.info(f"✅ Completed research for {artist_name} (confidence: {artist_info.confidence_score:.2f})")
            return artist_info
            
        except Exception as e:
            logger.error(f"❌ Error researching artist {artist_name}: {e}")
            artist_info.research_status = 'failed'
            return artist_info
    
    async def _find_official_website(self, artist_name: str) -> Optional[str]:
        """Find the official website for an artist."""
        try:
            # Try common domain patterns
            domain_patterns = [
                f"https://www.{artist_name.lower().replace(' ', '')}.com",
                f"https://{artist_name.lower().replace(' ', '')}.com",
                f"https://www.{artist_name.lower().replace(' ', '')}.net",
                f"https://{artist_name.lower().replace(' ', '')}.net"
            ]
            
            for domain in domain_patterns:
                try:
                    async with self.session.head(domain, timeout=10) as response:
                        if response.status == 200:
                            logger.info(f"🌐 Found official website: {domain}")
                            return domain
                except Exception:
                    continue
            
            # If no exact match, try searching
            search_url = f"https://www.google.com/search?q={artist_name.replace(' ', '+')}+official+website"
            # Note: In production, you'd use a proper search API
            
            return None
            
        except Exception as e:
            logger.debug(f"Error finding official website for {artist_name}: {e}")
            return None
    
    async def _research_official_website(self, website_url: str) -> Dict[str, Any]:
        """Research an artist's official website for information."""
        try:
            async with self.session.get(website_url, timeout=15) as response:
                if response.status != 200:
                    return {}
                
                html = await response.text()
                soup = HTMLParser(html)
                
                info = {}
                
                # Extract bio/description
                bio_selectors = [
                    'meta[name="description"]',
                    '.bio', '.about', '.description',
                    '[class*="bio"]', '[class*="about"]'
                ]
                
                for selector in bio_selectors:
                    element = soup.css_first(selector)
                    if element:
                        if selector.startswith('meta'):
                            bio = element.attributes.get('content', '')
                        else:
                            bio = element.text(strip=True)
                        
                        if bio and len(bio) > 20:
                            info['bio'] = bio[:500]  # Limit length
                            break
                
                # Extract hometown
                hometown_patterns = [
                    r'from\s+([A-Z][a-z]+(?:\s+[A-Z][a-z]+)*)',
                    r'hometown[:\s]+([A-Z][a-z]+(?:\s+[A-Z][a-z]+)*)',
                    r'based\s+in\s+([A-Z][a-z]+(?:\s+[A-Z][a-z]+)*)'
                ]
                
                text = soup.text()
                for pattern in hometown_patterns:
                    match = re.search(pattern, text, re.IGNORECASE)
                    if match:
                        info['hometown'] = match.group(1)
                        break
                
                # Extract active years
                year_patterns = [
                    r'(\d{4})\s*[-–]\s*(\d{4}|\bpresent\b)',
                    r'since\s+(\d{4})',
                    r'formed\s+in\s+(\d{4})'
                ]
                
                for pattern in year_patterns:
                    match = re.search(pattern, text, re.IGNORECASE)
                    if match:
                        if len(match.groups()) == 2:
                            info['active_years'] = f"{match.group(1)}-{match.group(2)}"
                        else:
                            info['active_years'] = f"{match.group(1)}-present"
                        break
                
                # Extract primary photo
                photo_selectors = [
                    'img[src*="band"]', 'img[src*="artist"]',
                    'img[src*="photo"]', 'img[src*="image"]',
                    '.hero img', '.main img', 'img[class*="hero"]'
                ]
                
                for selector in photo_selectors:
                    element = soup.css_first(selector)
                    if element:
                        src = element.attributes.get('src')
                        if src:
                            # Convert relative URLs to absolute
                            if src.startswith('/'):
                                src = urljoin(website_url, src)
                            elif not src.startswith('http'):
                                src = urljoin(website_url, src)
                            
                            info['primary_photo'] = src
                            break
                
                return info
                
        except Exception as e:
            logger.debug(f"Error researching website {website_url}: {e}")
            return {}
    
    async def _find_social_media(self, artist_name: str) -> Dict[str, str]:
        """Find social media profiles for an artist."""
        social_media = {}
        
        try:
            # Try common social media URL patterns
            for domain, platform in self.social_platforms.items():
                # Try different URL formats
                url_patterns = [
                    f"https://www.{domain}/{artist_name.lower().replace(' ', '')}",
                    f"https://{domain}/{artist_name.lower().replace(' ', '')}",
                    f"https://www.{domain}/{artist_name.lower().replace(' ', '.')}",
                    f"https://{domain}/{artist_name.lower().replace(' ', '.')}"
                ]
                
                for url in url_patterns:
                    try:
                        async with self.session.head(url, timeout=5) as response:
                            if response.status == 200:
                                social_media[platform] = url
                                logger.info(f"📱 Found {platform}: {url}")
                                break
                    except Exception:
                        continue
            
            return social_media
            
        except Exception as e:
            logger.debug(f"Error finding social media for {artist_name}: {e}")
            return social_media
    
    async def _classify_genre(self, artist_name: str, event_context: Dict[str, Any], artist_info: ArtistInfo) -> List[str]:
        """Classify artist genre based on context and research."""
        genres = []
        
        try:
            # Strategy 1: Use event context if available
            if event_context:
                venue_name = event_context.get('venue_name', '').lower()
                event_title = event_context.get('title', '').lower()
                
                # Venue-based genre hints
                if 'jazz' in venue_name or 'blues' in venue_name:
                    genres.append('jazz')
                elif 'rock' in venue_name or 'metal' in venue_name:
                    genres.append('rock')
                elif 'country' in venue_name or 'folk' in venue_name:
                    genres.append('country')
            
            # Strategy 2: Analyze artist name and bio for genre keywords
            text_to_analyze = f"{artist_name} {artist_info.bio or ''}"
            text_lower = text_to_analyze.lower()
            
            for genre, keywords in self.genre_keywords.items():
                for keyword in keywords:
                    if keyword in text_lower:
                        if genre not in genres:
                            genres.append(genre)
                        break
            
            # Strategy 3: Use social media platform hints
            if 'bandcamp' in artist_info.social_media:
                genres.append('indie')  # Bandcamp is often indie/alternative
            if 'spotify' in artist_info.social_media:
                # Could analyze Spotify genre data if API access available
                pass
            
            return genres[:3]  # Limit to top 3 genres
            
        except Exception as e:
            logger.debug(f"Error classifying genre for {artist_name}: {e}")
            return genres
    
    async def batch_research_artists(self, artist_names: List[str], event_contexts: List[Dict[str, Any]] = None) -> List[ArtistInfo]:
        """Research multiple artists in parallel."""
        if event_contexts is None:
            event_contexts = [{}] * len(artist_names)
        
        tasks = []
        for i, artist_name in enumerate(artist_names):
            context = event_contexts[i] if i < len(event_contexts) else {}
            task = self.research_artist(artist_name, context)
            tasks.append(task)
        
        # Research artists in parallel with rate limiting
        results = []
        for i in range(0, len(tasks), 5):  # Process 5 at a time
            batch = tasks[i:i+5]
            batch_results = await asyncio.gather(*batch, return_exceptions=True)
            
            for result in batch_results:
                if isinstance(result, Exception):
                    logger.error(f"Error in batch research: {result}")
                else:
                    results.append(result)
            
            # Rate limiting
            if i + 5 < len(tasks):
                await asyncio.sleep(1)
        
        return results
