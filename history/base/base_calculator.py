from typing import Any

from abc import ABC, abstractmethod

class HistoryCalculator(ABC):

    @abstractmethod

    def convert_history_to_platform_time(self, utc_timestamp: str) -> str:
        """Convert UTC timestamp string to platform-local time string."""
        pass