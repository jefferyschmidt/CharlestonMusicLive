from __future__ import annotations
from dataclasses import dataclass
from typing import Any, Dict, List, Optional

@dataclass
class ExtractResult:
    # Minimal normalized shape the extractor returns (pre-DB insert)
    site_slug: str
    venue_name: str
    title: str
    artist_name: Optional[str]
    starts_at_utc: str
    ends_at_utc: Optional[str]
    tz_name: str
    doors_time_utc: Optional[str]
    price_min: Optional[float]
    price_max: Optional[float]
    currency: str
    ticket_url: Optional[str]
    age_restriction: Optional[str]
    is_cancelled: bool
    source_url: str
    external_id: Optional[str]
    raw_data: Optional[Dict[str, Any]]  # lightweight structured payload for provenance

class Extractor:
    """Interface every venue/source extractor must implement."""

    def __init__(self, site_slug: str, source_url: str, tz_name: str = "America/New_York") -> None:
        self.site_slug = site_slug
        self.source_url = source_url
        self.tz_name = tz_name

    def parse(self, html: str) -> List[ExtractResult]:
        """Parse HTML (or JSON string) and return normalized events.
        Must be deterministic and side-effect free. No network calls here.
        """
        raise NotImplementedError
