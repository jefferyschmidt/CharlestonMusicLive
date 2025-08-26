import json
from pathlib import Path
import pytest

from collector.extractors.sample_venue import SampleVenueExtractor
from collector.extractors.base import ExtractResult

FIX_DIR = Path(__file__).parent / "fixtures" / "sample_venue"

def _load_text(p: Path) -> str:
    return p.read_text(encoding="utf-8")

def _load_json(p: Path):
    return json.loads(p.read_text(encoding="utf-8"))

def test_sample_venue_extractor_against_fixture():
    html = _load_text(FIX_DIR / "event_page.html")
    expected = _load_json(FIX_DIR / "event_expected.json")

    extractor = SampleVenueExtractor(site_slug="charleston", source_url="https://example.com/sample-venue/events")
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
