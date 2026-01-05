import logging

from datetime import datetime
from zoneinfo import ZoneInfo
import os

from history.base.base_calculator import HistoryCalculator

logger = logging.getLogger(__name__)

class Mt5HistoryCalculator(HistoryCalculator):
    def __init__(self):
        self.platform_timezone = os.environ.get("PLATFORM_TIMEZONE", "UTC")
        self.broker_zone = ZoneInfo(self.platform_timezone)

    def convert_history_to_platform_time(self, utc_timestamp: str) -> str:
        utc_time = datetime.strptime(utc_timestamp, "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=ZoneInfo("UTC"))
        broker_time = utc_time.astimezone(self.broker_zone)
        return broker_time.strftime("%Y-%m-%d %H:%M:%S")
