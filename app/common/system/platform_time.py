import time as _time
from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo
from typing import Optional, Dict
from functools import lru_cache

from app.common.config.constants import (
    DATETIME_FORMAT,
    DATE_FORMAT,
    TIME_FORMAT,
    MODE_LIVE,
    MODE_BACKTEST,
)
from app.common.models.model_strategy import MarketSession

@lru_cache(maxsize=100_000)
def _cached_strptime(value: str, fmt: str) -> datetime:
    return datetime.strptime(value, fmt)

class PlatformTime:
    _platform_tz: ZoneInfo = ZoneInfo("UTC")
    _mode: str = MODE_LIVE
    _backtest_timestamp: Optional[float] = None
    _offset: int = 0

    @staticmethod
    def set_timezone(tz_name: str) -> None:
        PlatformTime._platform_tz = ZoneInfo(tz_name or "UTC")    
    
    @staticmethod
    def set_offset(tz_offset: int) -> None:
        PlatformTime._offset = tz_offset 
 
    @staticmethod
    def set_mode(mode: str) -> None:
        PlatformTime._mode = mode

    @staticmethod
    def set_backtest_timestamp(ts: float) -> None:
        PlatformTime._backtest_timestamp = ts

    @staticmethod
    def clear_backtest_timestamp() -> None:
        PlatformTime._backtest_timestamp = None

    @staticmethod
    def now() -> datetime:
        return PlatformTime._get_now()

    @staticmethod
    def naive_now() -> datetime:
        return PlatformTime.now().replace(tzinfo=None)

    @staticmethod
    def timestamp() -> float:
        if PlatformTime._is_backtest():
            if PlatformTime._backtest_timestamp is None:
                raise RuntimeError("Backtest timestamp is not set in backtest mode.")
            return PlatformTime._backtest_timestamp
        return _time.time()

    @staticmethod
    def date():
        return PlatformTime.now().date()

    # @staticmethod
    # def weekday():
    #   return PlatformTime.now().weekday()

    @staticmethod
    def time_str() -> str:
        return PlatformTime.now().strftime(TIME_FORMAT)

    @staticmethod
    def date_str() -> str:
        return PlatformTime.now().strftime(DATE_FORMAT)

    @staticmethod
    def datetime_str() -> str:
        return PlatformTime.now().strftime(DATETIME_FORMAT)

    @staticmethod
    def iso() -> str:
        return PlatformTime.now().isoformat(timespec="seconds")

    @staticmethod
    def from_timestamp(ts: float, is_utc: bool = True) -> datetime:
        dt = datetime.fromtimestamp(ts, tz=timezone.utc if is_utc else PlatformTime._platform_tz)
        return PlatformTime.to_platform(dt) if is_utc else dt

    @staticmethod
    def to_platform(dt: datetime) -> datetime:
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt.astimezone(PlatformTime._platform_tz)

    @staticmethod
    def to_utc(dt: datetime) -> datetime:
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=PlatformTime._platform_tz)
        return dt.astimezone(timezone.utc)

    @staticmethod
    def parse_datetime_str(s: str) -> datetime:
        return datetime.strptime(s, DATETIME_FORMAT).replace(tzinfo=PlatformTime._platform_tz)

    @staticmethod
    def timedelta(**kwargs) -> timedelta:
        return timedelta(**kwargs)

    @staticmethod
    def local_now() -> datetime:
        return datetime.now()
    
    @staticmethod
    def local_now_utc() -> datetime:
        return datetime.now(tz=timezone.utc)

    @staticmethod
    def today():
        return PlatformTime.now().date()

    @staticmethod
    def combine(date_obj, time_obj) -> datetime:
        dt = datetime.combine(date_obj, time_obj)
        return dt.replace(tzinfo=PlatformTime._platform_tz)

    @staticmethod
    def replace(dt: datetime, **kwargs) -> datetime:
        return dt.replace(**kwargs)

    @staticmethod
    def min_datetime() -> datetime:
        return datetime.min.replace(tzinfo=PlatformTime._platform_tz)
   
    @staticmethod
    def strptime(value: str, fmt: str) -> datetime:
        return _cached_strptime(value, fmt).replace(tzinfo=PlatformTime._platform_tz)

    @staticmethod
    def strptime_utc(value: str, fmt: str) -> datetime:
        return _cached_strptime(value, fmt).replace(tzinfo=timezone.utc)

    @staticmethod
    def sleep(seconds: float) -> None:
        _time.sleep(seconds)

    @staticmethod
    def minutes_since_midnight(dt: Optional[datetime] = None) -> int:
        if dt is None:
            dt = PlatformTime.now()
        return dt.hour * 60 + dt.minute

    @staticmethod
    def compute_time_from_minutes(minutes: int):
        return (
            PlatformTime.now().replace(hour=0, minute=0, second=0, microsecond=0)
            + PlatformTime.timedelta(minutes=minutes)
        ).time()

    @staticmethod
    def is_within_time_window(open_min: int, close_min: int) -> bool:
        minutes = PlatformTime.minutes_since_midnight()
        return open_min <= minutes <= close_min

    @staticmethod
    def is_matching_weekday(target_day: int) -> bool:
        return PlatformTime.now().weekday() == (target_day - 1)

    @staticmethod
    def is_within_market_hours(day: str, sessions: Dict[str, MarketSession]) -> bool:
        if day not in sessions:
            return False
        now = PlatformTime.now().time()
        session = sessions[day]
        open_time = PlatformTime.strptime(session.open_time, "%H:%M").time()
        close_time = PlatformTime.strptime(session.close_time, "%H:%M").time()
        return open_time <= now <= close_time

    @staticmethod
    def parse_platform_timestamp(timestamp_str: str) -> datetime:
        return PlatformTime.strptime(timestamp_str, DATETIME_FORMAT)

    @staticmethod
    def to_mt_time_format(dt_str: str) -> str:
        return datetime.fromisoformat(dt_str.replace("Z", "")).strftime("%Y.%m.%d %H:%M:%S")

    @staticmethod
    def _is_backtest() -> bool:
        return PlatformTime._mode == MODE_BACKTEST

    @staticmethod
    def _get_now() -> datetime:
        if PlatformTime._is_backtest():
            if PlatformTime._backtest_timestamp is None:
                raise RuntimeError("Backtest timestamp is not set in backtest mode.")
            dt = datetime.fromtimestamp(PlatformTime._backtest_timestamp, tz=timezone.utc)
            return dt.astimezone(PlatformTime._platform_tz)

        base_dt = datetime.now(tz=PlatformTime._platform_tz)
        return base_dt + timedelta(hours=PlatformTime._offset)

    @staticmethod
    def parse_utc_timestamp_no_cache(value: str, fmt: str) -> int:
        dt = datetime.strptime(value, fmt)
        dt_utc = datetime(
            dt.year, dt.month, dt.day, dt.hour, dt.minute, dt.second,
            tzinfo=timezone.utc
        )
        return int(dt_utc.timestamp())

    @staticmethod
    def local_now_utc_timestamp() -> int:
        return int(datetime.now(tz=timezone.utc).timestamp())
