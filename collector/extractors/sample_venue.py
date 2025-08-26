from dataclasses import asdict
from typing import List, Optional
from selectolax.parser import HTMLParser

from .base import Extractor, ExtractResult

class SampleVenueExtractor(Extractor):
    def parse(self, html: str) -> List[ExtractResult]:
        tree = HTMLParser(html)
        events: List[ExtractResult] = []

        for node in tree.css("article.event"):
            title = (node.css_first(".title").text(strip=True) if node.css_first(".title") else "").strip()
            artist_name: Optional[str] = title or None
            date = node.css_first(".date").text(strip=True) if node.css_first(".date") else ""
            time_ = node.css_first(".time").text(strip=True) if node.css_first(".time") else ""
            venue_name = node.css_first(".venue").text(strip=True) if node.css_first(".venue") else "Sample Venue"
            external_id = node.attributes.get("data-external-id")
            ticket_url = node.css_first(".tickets").attributes.get("href") if node.css_first(".tickets") else None
            price_txt = node.css_first(".price").text(strip=True) if node.css_first(".price") else ""
            age = node.css_first(".age").text(strip=True) if node.css_first(".age") else None
            desc = node.css_first(".desc").text(strip=True) if node.css_first(".desc") else None

            # Very naive date→UTC; replace with robust parser later
            # Assume America/New_York and 24h time
            from datetime import datetime, timezone
            from zoneinfo import ZoneInfo
            local = ZoneInfo(self.tz_name)
            dt_local = datetime.fromisoformat(f"{date}T{time_}:00").replace(tzinfo=local)
            starts_at_utc = dt_local.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")

            price_min = price_max = None
            if "–" in price_txt or "-" in price_txt:
                p = price_txt.replace("$", "").replace("–", "-").split("-")
                try:
                    price_min = float(p[0]); price_max = float(p[1])
                except Exception:
                    pass
            elif price_txt.startswith("$"):
                try:
                    price_min = float(price_txt[1:]); price_max = price_min
                except Exception:
                    pass

            events.append(ExtractResult(
                site_slug=self.site_slug,
                venue_name=venue_name,
                title=title,
                artist_name=artist_name,
                starts_at_utc=starts_at_utc,
                ends_at_utc=None,
                tz_name=self.tz_name,
                doors_time_utc=None,
                price_min=price_min,
                price_max=price_max,
                currency="USD",
                ticket_url=ticket_url,
                age_restriction=age,
                is_cancelled=False,
                source_url=self.source_url,
                external_id=external_id,
                raw_data={"desc": desc} if desc else None,
            ))

        return events
