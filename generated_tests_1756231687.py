# tests/test_music_farm_extractor.py
import json
from pathlib import Path
import pytest

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

def test_music_farm_handles_empty_html():
    extractor = MusicFarmExtractor(site_slug="charleston", source_url="https://musicfarm.com/events")
    results = extractor.parse("")
    assert results == []

def test_music_farm_handles_no_events():
    html = "<html><body><div class='eventList'></div></body></html>"
    extractor = MusicFarmExtractor(site_slug="charleston", source_url="https://musicfarm.com/events")
    results = extractor.parse(html)
    assert results == []

def test_music_farm_price_parsing():
    # Test various price formats
    test_cases = [
        ("<div class='price'>Price: $25</div>", 25.0, 25.0),
        ("<div class='price'>Price: $25-$35</div>", 25.0, 35.0),
        ("<div class='price'>Price: $25 – $35</div>", 25.0, 35.0),
        ("<div class='price'>Price: Free</div>", 0.0, 0.0),
        ("<div class='price'>Price: TBA</div>", None, None),
    ]
    
    for html_snippet, expected_min, expected_max in test_cases:
        html = f"""
        <html><body>
            <div class='eventWrapper'>
                <div class='title'>Test Event</div>
                <div class='date'>Friday, January 1, 2023</div>
                <div class='time'>8:00PM</div>
                {html_snippet}
            </div>
        </body></html>
        """
        
        extractor = MusicFarmExtractor(site_slug="charleston", source_url="https://musicfarm.com/events")
        results = extractor.parse(html)
        
        assert len(results) == 1
        assert results[0].price_min == expected_min
        assert results[0].price_max == expected_max

def test_music_farm_cancelled_event():
    html = """
    <html><body>
        <div class='eventWrapper'>
            <div class='title'>Cancelled Show</div>
            <div class='date'>Friday, January 1, 2023</div>
            <div class='time'>8:00PM</div>
            <div class='status'>CANCELLED</div>
        </div>
    </body></html>
    """
    
    extractor = MusicFarmExtractor(site_slug="charleston", source_url="https://musicfarm.com/events")
    results = extractor.parse(html)
    
    assert len(results) == 1
    assert results[0].is_cancelled == True