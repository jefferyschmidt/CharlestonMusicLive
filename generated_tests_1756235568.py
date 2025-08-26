# tests/extractors/test_music_farm.py
import json
from pathlib import Path
import pytest
from datetime import datetime
from zoneinfo import ZoneInfo

from collector.extractors.music_farm import MusicFarmExtractor
from collector.extractors.base import ExtractResult

FIX_DIR = Path(__file__).parent / "fixtures" / "music_farm"

def _load_text(p: Path) -> str:
    return p.read_text(encoding="utf-8")

def _load_json(p: Path):
    return json.loads(p.read_text(encoding="utf-8"))

def test_music_farm_extractor_against_fixture():
    html = _load_text(FIX_DIR / "event_page.html")
    expected = _load_json(FIX_DIR / "event_expected.json")

    extractor = MusicFarmExtractor(site_slug="charleston", source_url="https://musicfarm.com/events")
    results = extractor.parse(html)

    # Convert dataclasses to dicts for comparison
    out = []
    for r in results:
        if isinstance(r, ExtractResult):
            d = r.__dict__.copy()
            d["raw_data_present"] = bool(d.pop("raw_data"))
            out.append(d)
        else:
            d = dict(r)
            d["raw_data_present"] = bool(d.pop("raw_data", None))
            out.append(d)

    assert out == expected

def test_parse_datetime():
    extractor = MusicFarmExtractor(site_slug="charleston", source_url="https://musicfarm.com/events")
    
    # Test valid date/time parsing
    result = extractor._parse_datetime("Fri, Dec 15", "Doors: 7:00 PM / Show: 8:00 PM")
    assert result is not None
    
    # Test invalid date/time
    result = extractor._parse_datetime("", "")
    assert result is None
    
    # Test with only doors time
    result = extractor._parse_datetime("Sat, Jan 20", "Doors: 7:00 PM")
    assert result is not None

def test_parse_price():
    extractor = MusicFarmExtractor(site_slug="charleston", source_url="https://musicfarm.com/events")
    
    # Test price range
    min_price, max_price = extractor._parse_price("$20-$25")
    assert min_price == 20.0
    assert max_price == 25.0
    
    # Test single price
    min_price, max_price = extractor._parse_price("$30")
    assert min_price == 30.0
    assert max_price == 30.0
    
    # Test free event
    min_price, max_price = extractor._parse_price("Free")
    assert min_price == 0.0
    assert max_price == 0.0
    
    # Test invalid price
    min_price, max_price = extractor._parse_price("Call for price")
    assert min_price is None
    assert max_price is None

def test_extract_age_restriction():
    extractor = MusicFarmExtractor(site_slug="charleston", source_url="https://musicfarm.com/events")
    
    # Create a mock node with age restriction
    from selectolax.parser import HTMLParser
    html = '<div class="event-card__details">21+ Only</div>'
    node = HTMLParser(html).css_first("div")
    
    # Test with a node containing age restriction
    age = extractor._extract_age_restriction(HTMLParser(html))
    assert age == "21+"
    
    # Test with All Ages
    html = '<div class="event-card__details">All Ages Welcome</div>'
    age = extractor._extract_age_restriction(HTMLParser(html))
    assert age == "All Ages"