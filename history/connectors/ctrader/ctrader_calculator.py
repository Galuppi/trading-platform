from typing import Any

from datetime import datetime
from zoneinfo import ZoneInfo
import os
from history.base.base_calculator import HistoryCalculator

class CTraderHistoryCalculator(HistoryCalculator):

    def __init__(self) -> Any:
        """Perform the defined operation."""
        self.platform_timezone = os.environ.get('PLATFORM_TIMEZONE', 'UTC')
        self.broker_zone = ZoneInfo(self.platform_timezone)

    def convert_history_to_platform_time(self, utc_timestamp: str) -> str:
        """Convert UTC timestamp string to broker-local timestamp string (YYYY-MM-DD HH:MM:SS)."""
        utc_time = datetime.strptime(utc_timestamp, '%Y-%m-%dT%H:%M:%SZ').replace(tzinfo=ZoneInfo('UTC'))
        broker_time = utc_time.astimezone(self.broker_zone)
        return broker_time.strftime('%Y-%m-%d %H:%M:%S')