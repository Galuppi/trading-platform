import MetaTrader5 as mt5
import pandas as pd
import logging
from datetime import datetime, timezone
from dateutil.relativedelta import relativedelta

from history.common.config.constants import (
    TIMEFRAME_M1,
    TIMEFRAME_M5,
    TIMEFRAME_M15,
    TIMEFRAME_M30,
    TIMEFRAME_H1,
    TIMEFRAME_H4,
    TIMEFRAME_D1,
)

from history.base.base_history import History
from history.base.base_calculator import HistoryCalculator

logger = logging.getLogger(__name__)

TIMEFRAME_MAP = {
    TIMEFRAME_M1: mt5.TIMEFRAME_M1,
    TIMEFRAME_M5: mt5.TIMEFRAME_M5,
    TIMEFRAME_M15: mt5.TIMEFRAME_M15,
    TIMEFRAME_M30: mt5.TIMEFRAME_M30,
    TIMEFRAME_H1: mt5.TIMEFRAME_H1,
    TIMEFRAME_H4: mt5.TIMEFRAME_H4,
    TIMEFRAME_D1: mt5.TIMEFRAME_D1,
}


class Mt5History(History):
    def __init__(self, calculator: HistoryCalculator):
        self.calculator = calculator

    def get_historical_data(
        self,
        symbol: str,
        timeframe: str,
        start_date: datetime,
        end_date: datetime
    ) -> pd.DataFrame:
        if not mt5.initialize():
            raise RuntimeError("MT5 initialization failed")

        mt5_timeframe = TIMEFRAME_MAP.get(timeframe)
        if mt5_timeframe is None:
            raise ValueError(f"Unsupported timeframe: {timeframe}")

        all_data = []
        current_start = start_date

        while current_start < end_date:
            current_end = current_start + relativedelta(months=1)
            if current_end > end_date:
                current_end = end_date

            start_utc = current_start.astimezone(timezone.utc)
            end_utc = current_end.astimezone(timezone.utc)

            rates = mt5.copy_rates_range(symbol, mt5_timeframe, start_utc, end_utc)

            if rates is None or len(rates) == 0:
                logger.warning(f"No data returned for {symbol} — "
                               f"{start_utc.date()} to {end_utc.date()}")
            else:
                batch = pd.DataFrame(rates)
                batch["time"] = pd.to_datetime(batch["time"], unit="s")
                batch["time"] = batch["time"].dt.strftime("%Y-%m-%dT%H:%M:%SZ")
                batch["time"] = batch["time"].apply(self.calculator.convert_history_to_platform_time)
                batch = batch[["time", "open", "high", "low", "close", "tick_volume"]]
                batch.rename(columns={"tick_volume": "volume"}, inplace=True)
                all_data.append(batch)

            current_start = current_end

        mt5.shutdown()

        if not all_data:
            raise RuntimeError(f"No data returned for {symbol} {timeframe}")

        full_data = pd.concat(all_data, ignore_index=True).drop_duplicates(subset=["time"])
        return full_data
