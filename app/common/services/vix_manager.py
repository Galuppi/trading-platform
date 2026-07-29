"""Tracks and exposes the current VIX (market volatility) reading, independent of any strategy."""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Optional

from app.common.models.model_vix import VixReading
from app.common.services.platform_time import PlatformTime
from app.common.config.paths import VIX_FEED_PATH

logger = logging.getLogger(__name__)

STALE_AFTER = PlatformTime.timedelta(hours=1)


class VixManager:
    """Tracks and exposes the current VIX reading."""

    def __init__(self) -> None:
        self.reading: Optional[VixReading] = None

    def _read_source(self) -> Optional[float]:
        """Read the raw VIX value from the configured feed."""
        feed_path = Path(VIX_FEED_PATH)
        if not feed_path.exists():
            return None

        raw_text = feed_path.read_text(encoding="utf-8")
        if not raw_text.strip():
            return None

        payload = json.loads(raw_text)
        timestamp_text = payload.get("timestamp")
        if not timestamp_text:
            return None

        feed_time = PlatformTime.strptime(timestamp_text, "%Y-%m-%d %H:%M").replace(tzinfo=None)
        age = PlatformTime.local_now() - feed_time
        if age > STALE_AFTER:
            return None

        return payload.get("vix")

    def refresh(self) -> None:
        """Pull a fresh VIX reading; keeps the last known value if the read fails or is stale."""
        try:
            raw_value = self._read_source()
            if raw_value is None:
                logger.warning("VIX feed unavailable or stale, keeping last known reading")
                return
            self.reading = VixReading(value=float(raw_value), read_at=PlatformTime.now())
        except Exception as error:
            logger.warning(f"VIX refresh failed, keeping last known reading: {error}")

    @property
    def value(self) -> Optional[float]:
        """Return the last known VIX value, or None if none has ever been read."""
        return self.reading.value if self.reading else None

    def get_reading(self) -> Optional[VixReading]:
        """Return the full last known VIX reading, value and timestamp."""
        return self.reading

    def is_paused(self, threshold: float) -> bool:
        """Return True when the last known VIX value exceeds the given threshold."""
        current_value = self.value
        return current_value is not None and current_value > threshold
