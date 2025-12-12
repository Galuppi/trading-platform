import os

from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

from app.common.models.model_engine import TestPeriod, Timestamps
from app.common.config.constants import (
    TIMEFRAME_M1, TIMEFRAME_M5, TIMEFRAME_M15,
    TIMEFRAME_M30, TIMEFRAME_H1, TIMEFRAME_H4, TIMEFRAME_D1
)

TIMEFRAME_STEP_MAP = {
    TIMEFRAME_M1: timedelta(minutes=1),
    TIMEFRAME_M5: timedelta(minutes=5),
    TIMEFRAME_M15: timedelta(minutes=15),
    TIMEFRAME_M30: timedelta(minutes=30),
    TIMEFRAME_H1: timedelta(hours=1),
    TIMEFRAME_H4: timedelta(hours=4),
    TIMEFRAME_D1: timedelta(days=1),
}


def load_tester_setup() -> tuple[TestPeriod, Timestamps]:
    date_from_str = os.environ["BACKTEST_DATE_FROM"]
    date_to_str = os.environ["BACKTEST_DATE_TO"]
    timeframe = os.environ["BACKTEST_TIMEFRAME"]
    timezone_str = os.environ["PLATFORM_TIMEZONE"]

    tz = ZoneInfo(timezone_str)

    date_from = datetime.strptime(date_from_str, "%d-%m-%Y").replace(tzinfo=None).astimezone(tz)
    date_to = datetime.strptime(date_to_str, "%d-%m-%Y").replace(tzinfo=None).astimezone(tz)

    period = TestPeriod(date_from=date_from, date_to=date_to, timeframe=timeframe)

    step = TIMEFRAME_STEP_MAP[timeframe]
    current = date_from
    values = []

    while current <= date_to:
        values.append(int(current.timestamp()))
        current += step

    return period, Timestamps(values=values)
