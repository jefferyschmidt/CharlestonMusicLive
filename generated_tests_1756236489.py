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
    
    # Test standard format
    result = extractor._parse_datetime("Friday, October 15, 2023", "8:00 PM")
    dt = datetime.fromisoformat("2023-10-15T20:00:00").replace(tzinfo=ZoneInfo("America/New_York"))
    expected = dt.astimezone(datetime.UTC).isoformat().replace("+00:00", "Z")
    assert result == expected
    
    # Test AM time
    result = extractor._parse_datetime("Saturday, November 20, 2023", "11:30 AM")
    dt = datetime.fromisoformat("2023-11-20T11:30:00").replace(tzinfo=ZoneInfo("America/New_York"))
    expected = dt.astimezone(datetime.UTC).isoformat().replace("+00:00", "Z")
    assert result == expected

def test_parse_price():
    extractor = MusicFarmExtractor(site_slug="charleston", source_url="https://musicfarm.com/events")
    
    # Test single price
    assert extractor._parse_price("$25") == (25.0, 25.0)
    
    # Test price range with hyphen
    assert extractor._parse_price("$15-$20") == (15.0, 20.0)
    
    # Test price range with en dash
    assert extractor._parse_price("$15 – $20") == (15.0, 20.0)
    
    # Test empty price
    assert extractor._parse_price("") == (None, None)
    
    # Test non-numeric price
    assert extractor._parse_price("Free") == (None, None)