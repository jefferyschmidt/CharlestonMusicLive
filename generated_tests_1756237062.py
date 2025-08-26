# tests/extractors/test_music_farm.py
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

    # Convert dataclasses to dicts if needed
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

def test_music_farm_price_parsing():
    extractor = MusicFarmExtractor(site_slug="charleston", source_url="https://musicfarm.com/events")
    
    # Test various price formats
    assert extractor._parse_price("$15") == (15.0, 15.0)
    assert extractor._parse_price("$15-20") == (15.0, 20.0)
    assert extractor._parse_price("$15 - $20") == (15.0, 20.0)
    assert extractor._parse_price("Free") == (None, None)
    assert extractor._parse_price("TBD") == (None, None)
    assert extractor._parse_price("") == (None, None)

def test_music_farm_datetime_parsing():
    extractor = MusicFarmExtractor(site_slug="charleston", source_url="https://musicfarm.com/events")
    
    # Test various date/time formats
    result = extractor._parse_datetime("FRI, JAN 12", "Doors: 8:00 PM")
    assert "T20:00:00Z" in result  # 8 PM converted to UTC
    
    result = extractor._parse_datetime("January 15", "9:30 PM")
    assert "T21:30:00Z" in result  # 9:30 PM converted to UTC