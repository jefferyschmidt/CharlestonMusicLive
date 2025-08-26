"""
Test the Music Farm Charleston extractor.
"""
import json
import pytest
from pathlib import Path
from collector.extractors.music_farm import MusicFarmExtractor


def test_music_farm_extractor_parses_fixture():
    """Test that the Music Farm extractor correctly parses the test fixture."""
    # Load the test fixture
    fixture_path = Path(__file__).parent / "fixtures" / "music_farm" / "event_page.html"
    with open(fixture_path, 'r', encoding='utf-8') as f:
        html_content = f.read()
    
    # Load the expected results
    expected_path = Path(__file__).parent / "fixtures" / "music_farm" / "event_expected.json"
    with open(expected_path, 'r', encoding='utf-8') as f:
        expected_results = json.load(f)
    
    # Create extractor and parse
    extractor = MusicFarmExtractor(
        site_slug="charleston",
        source_url="https://example.com/music-farm/events"
    )
    
    results = extractor.parse(html_content)
    
    # Verify we got the expected number of events
    assert len(results) == len(expected_results), f"Expected {len(expected_results)} events, got {len(results)}"
    
    # Verify each event matches expectations
    for i, (result, expected) in enumerate(zip(results, expected_results)):
        assert result.site_slug == expected["site_slug"], f"Event {i}: site_slug mismatch"
        assert result.venue_name == expected["venue_name"], f"Event {i}: venue_name mismatch"
        assert result.title == expected["title"], f"Event {i}: title mismatch"
        assert result.artist_name == expected["artist_name"], f"Event {i}: artist_name mismatch"
        assert result.starts_at_utc == expected["starts_at_utc"], f"Event {i}: starts_at_utc mismatch"
        assert result.ends_at_utc == expected["ends_at_utc"], f"Event {i}: ends_at_utc mismatch"
        assert result.tz_name == expected["tz_name"], f"Event {i}: tz_name mismatch"
        assert result.price_min == expected["price_min"], f"Event {i}: price_min mismatch"
        assert result.price_max == expected["price_max"], f"Event {i}: price_max mismatch"
        assert result.currency == expected["currency"], f"Event {i}: currency mismatch"
        assert result.ticket_url == expected["ticket_url"], f"Event {i}: ticket_url mismatch"
        assert result.age_restriction == expected["age_restriction"], f"Event {i}: age_restriction mismatch"
        assert result.is_cancelled == expected["is_cancelled"], f"Event {i}: is_cancelled mismatch"
        assert result.source_url == expected["source_url"], f"Event {i}: source_url mismatch"
        assert result.external_id == expected["external_id"], f"Event {i}: external_id mismatch"
        
        # Verify raw_data contains expected debugging info
        assert "title" in result.raw_data, f"Event {i}: raw_data missing title"
        assert "artist_name" in result.raw_data, f"Event {i}: raw_data missing artist_name"
        assert "date_text" in result.raw_data, f"Event {i}: raw_data missing date_text"
        assert "price_text" in result.raw_data, f"Event {i}: raw_data missing price_text"
        assert "age_text" in result.raw_data, f"Event {i}: raw_data missing age_text"
        assert "element_html" in result.raw_data, f"Event {i}: raw_data missing element_html"


def test_music_farm_extractor_handles_empty_html():
    """Test that the extractor handles empty HTML gracefully."""
    extractor = MusicFarmExtractor()
    results = extractor.parse("")
    assert results == []


def test_music_farm_extractor_handles_malformed_html():
    """Test that the extractor handles malformed HTML gracefully."""
    extractor = MusicFarmExtractor()
    results = extractor.parse("<html><body><div>Not an event</div></body></html>")
    assert results == []


def test_music_farm_extractor_venue_name():
    """Test that the extractor has the correct venue name."""
    extractor = MusicFarmExtractor()
    assert extractor.venue_name == "The Music Farm"


def test_music_farm_extractor_timezone():
    """Test that the extractor has the correct timezone."""
    extractor = MusicFarmExtractor()
    assert extractor.tz_name == "America/New_York"
