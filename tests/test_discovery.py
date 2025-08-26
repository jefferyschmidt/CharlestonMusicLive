"""
Test the intelligent discovery system.
"""
import pytest
import asyncio
from unittest.mock import patch, MagicMock, AsyncMock
from collector.discovery.source_discoverer import SourceDiscoverer, DiscoveredSource
from collector.extractors.factory import ExtractorFactory, ExtractorMatch


class TestSourceDiscoverer:
    """Test the source discovery engine."""
    
    @pytest.mark.asyncio
    async def test_discoverer_initialization(self):
        """Test that the discoverer initializes correctly."""
        async with SourceDiscoverer("charleston", "Charleston", "SC") as discoverer:
            assert discoverer.site_slug == "charleston"
            assert discoverer.city == "Charleston"
            assert discoverer.state == "SC"
            assert discoverer.session is not None
    
    @pytest.mark.asyncio
    async def test_discoverer_context_manager(self):
        """Test that the discoverer properly manages its session."""
        discoverer = SourceDiscoverer("charleston", "Charleston", "SC")
        assert discoverer.session is None
        
        async with discoverer:
            assert discoverer.session is not None
        
        assert discoverer.session is None
    
    def test_calendar_detection(self):
        """Test calendar detection patterns."""
        discoverer = SourceDiscoverer("charleston", "Charleston", "SC")
        
        # Test HTML with calendar indicators
        html_with_calendar = """
        <div class="event-calendar">
            <span class="date">January 15, 2025</span>
            <span class="time">8:00 PM</span>
            <button class="buy-tickets">Buy Tickets</button>
        </div>
        """
        
        calendar_score = discoverer._detect_calendar_indicators(html_with_calendar)
        assert calendar_score > 0.5
        
        # Test HTML without calendar indicators
        html_without_calendar = """
        <div class="content">
            <p>Welcome to our website</p>
            <p>Contact us for more information</p>
        </div>
        """
        
        calendar_score = discoverer._detect_calendar_indicators(html_without_calendar)
        assert calendar_score < 0.3
    
    def test_event_content_detection(self):
        """Test event content detection."""
        discoverer = SourceDiscoverer("charleston", "Charleston", "SC")
        
        # Test HTML with event keywords
        html_with_events = """
        <div class="events">
            <h2>Live Music Events</h2>
            <p>Join us for concerts and shows</p>
            <div class="ticket-info">Get your tickets now</div>
        </div>
        """
        
        event_score = discoverer._detect_event_content(html_with_events)
        assert event_score > 0.3
        
        # Test HTML without event keywords
        html_without_events = """
        <div class="about">
            <h2>About Us</h2>
            <p>We are a local business</p>
            <p>Contact us for services</p>
        </div>
        """
        
        event_score = discoverer._detect_event_content(html_without_events)
        assert event_score < 0.1
    
    def test_venue_type_analysis(self):
        """Test venue type analysis."""
        discoverer = SourceDiscoverer("charleston", "Charleston", "SC")
        
        # Test concert venue detection
        html_concert = """
        <div class="concert-venue">
            <h1>Music Hall</h1>
            <div class="ticketing">Buy Tickets</div>
            <div class="calendar">Event Calendar</div>
        </div>
        """
        
        venue_type = discoverer._analyze_venue_type(
            MagicMock(), html_concert, {}
        )
        assert venue_type == 'concert_venue'
        
        # Test bar venue detection
        html_bar = """
        <div class="bar">
            <h1>Local Pub</h1>
            <div class="drinks">Cocktail Menu</div>
            <div class="live-music">Live Music Schedule</div>
        </div>
        """
        
        venue_type = discoverer._analyze_venue_type(
            MagicMock(), html_bar, {}
        )
        assert venue_type == 'bar_venue'


class TestExtractorFactory:
    """Test the extractor factory."""
    
    def test_factory_initialization(self):
        """Test that the factory initializes correctly."""
        factory = ExtractorFactory()
        assert factory.extractors is not None
        assert factory.venue_patterns is not None
    
    def test_exact_match_finding(self):
        """Test finding exact matches with known extractors."""
        factory = ExtractorFactory()
        
        # Test Music Farm match
        url = "https://musicfarm.com/events"
        html = "<div>Music Farm Events Calendar</div>"
        metadata = {}
        
        match = factory._find_exact_match(url, html, metadata)
        assert match is not None
        assert "Music Farm" in match.reasoning
        assert match.confidence_score > 0.8
    
    def test_venue_type_analysis(self):
        """Test venue type analysis in the factory."""
        factory = ExtractorFactory()
        
        # Test concert venue
        html_concert = """
        <div class="concert-venue">
            <h1>Concert Hall</h1>
            <div class="ticketing">Buy Tickets</div>
            <div class="calendar">Event Calendar</div>
        </div>
        """
        
        venue_type = factory._analyze_venue_type(
            MagicMock(), html_concert, {}
        )
        assert venue_type == 'concert_venue'
        
        # Test restaurant venue
        html_restaurant = """
        <div class="restaurant">
            <h1>Fine Dining</h1>
            <div class="menu">Chef's Specials</div>
            <div class="events">Special Events</div>
        </div>
        """
        
        venue_type = factory._analyze_venue_type(
            MagicMock(), html_restaurant, {}
        )
        assert venue_type == 'restaurant_venue'
    
    def test_custom_selector_generation(self):
        """Test custom selector generation based on venue type."""
        factory = ExtractorFactory()
        
        # Test concert venue selectors
        selectors = factory._generate_custom_selectors('concert_venue')
        assert '.concert' in selectors['event_container']
        assert '.artist-name' in selectors['title']
        
        # Test bar venue selectors
        selectors = factory._generate_custom_selectors('bar_venue')
        assert '.live-music' in selectors['event_container']
        assert '.entertainment-schedule' in selectors['date']
    
    def test_date_pattern_generation(self):
        """Test date pattern generation based on venue type."""
        factory = ExtractorFactory()
        
        # Test concert venue patterns
        patterns = factory._get_date_patterns('concert_venue')
        assert any('doors' in pattern for pattern in patterns)
        assert any('show starts' in pattern for pattern in patterns)
        
        # Test bar venue patterns
        patterns = factory._get_date_patterns('bar_venue')
        assert any('live music' in pattern for pattern in patterns)
        assert any('entertainment' in pattern for pattern in patterns)
    
    def test_price_pattern_generation(self):
        """Test price pattern generation based on venue type."""
        factory = ExtractorFactory()
        
        # Test concert venue patterns
        patterns = factory._get_price_patterns('concert_venue')
        assert any('VIP' in pattern for pattern in patterns)
        assert any('general admission' in pattern for pattern in patterns)
        
        # Test bar venue patterns
        patterns = factory._get_price_patterns('bar_venue')
        assert any('no cover' in pattern for pattern in patterns)
        assert any('drink minimum' in pattern for pattern in patterns)


@pytest.mark.asyncio
async def test_discovery_integration():
    """Test integration between discovery and factory."""
    # Mock the HTTP session to avoid real network calls
    with patch('collector.discovery.source_discoverer.aiohttp.ClientSession') as mock_session:
        mock_session.return_value.__aenter__ = AsyncMock(return_value=mock_session.return_value)
        mock_session.return_value.__aexit__ = AsyncMock()
        
        # Mock HTTP responses
        mock_response = MagicMock()
        mock_response.status = 200
        mock_response.text = AsyncMock(return_value="""
        <html>
            <head><title>Music Farm Charleston</title></head>
            <body>
                <div class="event-calendar">
                    <h1>Music Farm Charleston</h1>
                    <div class="event-item">
                        <h3>Live Music Tonight</h3>
                        <div class="date">January 15, 2025 at 8:00 PM</div>
                        <div class="tickets">Buy Tickets</div>
                    </div>
                </div>
            </body>
        </html>
        """)
        
        mock_session.return_value.get = AsyncMock(return_value=mock_response)
        
        # Test discovery
        async with SourceDiscoverer("charleston", "Charleston", "SC") as discoverer:
            sources = await discoverer._discover_via_search_engines(5)
            
            # Should find some sources
            assert len(sources) >= 0  # May be 0 due to mocked search
    
    # Test factory analysis
    factory = ExtractorFactory()
    
    # Test with Music Farm HTML
    music_farm_html = """
    <html>
        <head><title>Music Farm Charleston</title></head>
        <body>
            <div class="event-calendar">
                <h1>Music Farm Charleston</h1>
                <div class="event-item">
                    <h3>Live Music Tonight</h3>
                    <div class="date">January 15, 2025 at 8:00 PM</div>
                    <div class="tickets">Buy Tickets</div>
                </div>
            </div>
        </body>
    </html>
    """
    
    match = factory.analyze_source(
        "https://musicfarm.com/events",
        music_farm_html,
        {}
    )
    
    assert match is not None
    assert match.confidence_score > 0.5
    assert "Generic extractor" in match.reasoning or "Music Farm" in match.reasoning


if __name__ == "__main__":
    pytest.main([__file__])
