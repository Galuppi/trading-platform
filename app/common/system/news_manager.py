from __future__ import annotations

import csv
import logging
from typing import Dict, List, Optional, Tuple

import urllib.request

from app.common.system.platform_time import PlatformTime
from app.common.models.model_news import FaireconomyEvent, ImpactLevel
from app.common.config.paths import NEWS_URL

logger = logging.getLogger(__name__)


IMPACT_MAPPING: Dict[str, ImpactLevel] = {
    "Low": "Low",
    "Medium": "Medium",
    "High": "High",
    "Holiday": "Holiday",
    "Non-Economic": "Low",
    "red": "High",
    "yellow": "Medium",
    "orange": "Medium",
    "gray": "Low",
    "green": "Low",
}


class NewsManager:
    def __init__(self, window_minutes: int = 10) -> None:
        self.events: List[FaireconomyEvent] = []
        self.window_seconds = window_minutes * 60

    def _parse_event_timestamp(
        self,
        date_value: str,
        time_value: str
    ) -> Tuple[Optional[int], str]:
        time_text = (time_value or "").strip()
        date_text = (date_value or "").strip()

        if not date_text or date_text.lower() == "nan":
            return None, time_text

        lower_time = time_text.lower()
        if not time_text or "day" in lower_time or "tentative" in lower_time:
            return None, time_text

        cleaned_time = (
            time_text.upper()
            .replace("AM", " AM")
            .replace("PM", " PM")
        )
        combined_string = f"{date_text} {cleaned_time}"

        formats_to_try = [
            "%m-%d-%Y %I:%M %p",
            "%Y-%m-%d %I:%M %p",
            "%Y-%m-%d %H:%M",
            "%Y-%m-%d %H:%M:%S",
        ]

        for fmt in formats_to_try:
            try:
                timestamp = PlatformTime.parse_utc_timestamp_no_cache(combined_string, fmt)
                return timestamp, time_text
            except ValueError:
                continue

        return None, time_text

    def _get_impact_level(self, raw_value: str) -> ImpactLevel:
        key = (raw_value or "").strip()
        impact = IMPACT_MAPPING.get(key, "Low")
        return impact

    def _sort_key(self, event: FaireconomyEvent) -> Tuple[float, int]:
        timestamp = float(event.timestamp) if event.timestamp is not None else float("inf")
        order: Dict[ImpactLevel, int] = {
            "High": 0,
            "Medium": 1,
            "Low": 2,
            "Holiday": 3,
        }
        return timestamp, order[event.impact]

    def _sort_events_by_time_and_impact(
        self,
        events: List[FaireconomyEvent]
    ) -> List[FaireconomyEvent]:
        return sorted(events, key=self._sort_key)

    def _download_and_parse_calendar(self) -> List[FaireconomyEvent]:
        request = urllib.request.Request(
            NEWS_URL,
            headers={
                "User-Agent": (
                    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                    "AppleWebKit/537.36"
                )
            }
        )
        try:
            with urllib.request.urlopen(request, timeout=10) as response:
                data_bytes = response.read()
        except urllib.error.HTTPError as error:
            if error.code == 429:
                logger.warning("Calendar refresh skipped: rate limit reached (HTTP 429)")
                return []
            logger.error(f"Calendar download failed: {error}")
            return []

        try:
            text_data = data_bytes.decode("utf-8", errors="replace")
        except Exception as error:
            logger.error("Calendar decoding failed: %s", error)
            return []

        rows = text_data.splitlines()
        reader = csv.DictReader(rows)
        events: List[FaireconomyEvent] = []

        for row in reader:
            if not row:
                continue

            date_text = row.get("Date", "") or ""
            time_text = row.get("Time", "") or ""
            country_text = row.get("Country", "") or ""
            impact_text = row.get("Impact", "") or ""
            title_text = row.get("Title", "") or ""

            forecast_raw = row.get("Forecast", "")
            forecast = forecast_raw.strip() if forecast_raw and forecast_raw.strip() else None

            previous_raw = row.get("Previous", "")
            previous = previous_raw.strip() if previous_raw and previous_raw.strip() else None

            timestamp, display_time = self._parse_event_timestamp(
                date_text,
                time_text
            )
            impact = self._get_impact_level(impact_text)

            event = FaireconomyEvent(
                date=date_text,
                timestamp=timestamp,
                time=display_time,
                country=country_text,
                impact=impact,
                title=title_text,
                forecast=forecast,
                previous=previous,
            )
            events.append(event)

        return self._sort_events_by_time_and_impact(events)

    def refresh(self) -> None:
        parsed_events = self._download_and_parse_calendar()
        if parsed_events:
            self.events = parsed_events
            logger.info("News calendar updated — %d events", len(parsed_events))
        else:
            if not self.events:
                logger.warning("Calendar update failed; no previous events available")
            else:
                logger.warning(
                    "Calendar update failed; retaining previous %d events",
                    len(self.events)
                )

    def _country_affects_symbol(
        self,
        symbol: str,
        country: str
    ) -> bool:
        if not country:
            return False

        if country == "All":
            return True

        symbol_upper = symbol.upper()
        country_upper = country.upper()

        if len(country_upper) >= 2 and symbol_upper.startswith(country_upper[:2]):
            return True

        if (
            len(symbol_upper) >= 6
            and symbol_upper[:3].isalpha()
            and symbol_upper[3:6].isalpha()
        ):
            base = symbol_upper[:3]
            quote = symbol_upper[3:6]
            if country_upper in {base, quote}:
                return True

        if country_upper == "USD" and (
            "USD" in symbol_upper or symbol_upper.startswith("US")
        ):
            return True

        return False

    def is_releasing_news(
        self,
        symbol: Optional[str] = None
    ) -> bool:
        now_ts = PlatformTime.local_now_utc_timestamp()
        window = self.window_seconds

        for event in self.events:
            if event.impact != "High":
                continue
            if event.timestamp is None:
                continue

            start = event.timestamp - window
            end = event.timestamp + window

            if start <= now_ts <= end:
                if symbol is None:
                    return True
                if self._country_affects_symbol(symbol, event.country):
                    return True

        return False

    def get_releasing_event(
        self,
        symbol: Optional[str] = None
    ) -> Optional[FaireconomyEvent]:
        now_ts = PlatformTime.local_now_utc_timestamp()
        window = self.window_seconds

        for event in self.events:
            if event.impact != "High":
                continue
            if event.timestamp is None:
                continue

            start = event.timestamp - window
            end = event.timestamp + window

            if start <= now_ts <= end:
                if symbol is None:
                    return event
                if self._country_affects_symbol(symbol, event.country):
                    return event

        return None
