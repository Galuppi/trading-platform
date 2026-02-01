import logging
import pandas as pd
from typing import Optional, List
from pathlib import Path
from datetime import datetime, timedelta
import MetaTrader5 as mt5

from app.base.base_symbol import Symbol
from app.common.models.model_symbol import Range, SymbolInfo, PriceRecord
from app.common.config.paths import DATA_PATH
from app.common.services.platform_time import PlatformTime

logger = logging.getLogger(__name__)


class Mt5testerSymbol(Symbol):
    def __init__(self, backtester_config=None, account=None):
        self.account = account
        self.backtester_config = backtester_config
        self.data_by_symbol = {}
        self.symbol_info_cache = {}
        self.load_historical_data()
        self.preload_symbol_info()

    def load_historical_data(self):
        timeframe = self.backtester_config.backtest_timeframe.upper()
        data_root_path = DATA_PATH

        for symbol_path in data_root_path.iterdir():
            if symbol_path.is_dir():
                symbol = symbol_path.name.upper()
                file_pattern = f"*_{timeframe}.csv"
                all_dfs = []

                for csv_file in symbol_path.glob(file_pattern):
                    df = pd.read_csv(csv_file, parse_dates=["time"])
                    df.drop_duplicates(subset="time", inplace=True)
                    all_dfs.append(df)

                if all_dfs:
                    combined_df = pd.concat(all_dfs)
                    combined_df.set_index("time", inplace=True)
                    combined_df.sort_index(inplace=True)
                    self.data_by_symbol[symbol] = combined_df

    def preload_symbol_info(self):
        if not mt5.initialize():
            raise RuntimeError(f"Failed to initialize MT5: {mt5.last_error()}")

        for symbol in self.data_by_symbol.keys():
            symbol = symbol.replace(".CASH", ".cash")
            info = mt5.symbol_info(symbol)
            if not info:
                logger.warning(f"Symbol info not found for {symbol}")
                continue
            self.symbol_info_cache[symbol.upper()] = info

        logger.info(f"Preloaded symbol info for {len(self.symbol_info_cache)} symbols.")

    def _get_mt5_info(self, symbol: str):
        info = self.symbol_info_cache.get(symbol.upper())
        if not info:
            raise RuntimeError(f"Missing symbol info for {symbol}. Make sure it's preloaded.")
        return info

    def get_symbol_info(self, symbol: str, timestamp: datetime) -> SymbolInfo:
        symbol = symbol.upper()
        timestamp = timestamp.replace(tzinfo=None)
        df = self.data_by_symbol.get(symbol)

        if df is None:
            raise ValueError(f"No historical data loaded for symbol: {symbol}")

        if timestamp not in df.index:
            timestamp = df.index.asof(timestamp)

        if timestamp is None or timestamp not in df.index:
            raise ValueError(f"No data for {symbol} at or before {timestamp}")

        row = df.loc[timestamp]

        return SymbolInfo(
            symbol=symbol,
            time=timestamp,
            ask_price=row["close"],
            bid_price=row["close"],
            open=row["open"],
            high=row["high"],
            low=row["low"],
            close=row["close"],
            lot_size=row["volume"]
        )

    def get_symbol_data_range(self, symbol: str, start_time: datetime, end_time: datetime) -> List[PriceRecord]:
        symbol = symbol.upper()
        df = self.data_by_symbol.get(symbol)

        if df is None:
            raise ValueError(f"No data for symbol: {symbol}")

        start_time = start_time.replace(tzinfo=None)
        end_time = end_time.replace(tzinfo=None)

        try:
            sliced = df.loc[start_time:end_time]
        except KeyError:
            return []

        return [
            PriceRecord(
                symbol=symbol,
                time=row.Index,
                open=row.open,
                high=row.high,
                low=row.low,
                close=row.close,
                volume=row.volume,
            )
            for row in sliced.itertuples()
        ]

    def get_high_low_range(self, symbol: str, start_minute: int, end_minute: int) -> Range:
        now = PlatformTime.now().replace(second=0, microsecond=0)
        start_time = now.replace(hour=0, minute=0) + timedelta(minutes=start_minute)
        end_time = now.replace(hour=0, minute=0) + timedelta(minutes=end_minute)

        try:
            records = self.get_symbol_data_range(symbol, start_time, end_time)
        except ValueError:
            return Range(symbol=symbol, high=0.0, low=0.0, date=start_time.date(), range_set=False)

        highs = [r.high for r in records]
        lows = [r.low for r in records]

        return Range(
            symbol=symbol,
            high=max(highs),
            low=min(lows),
            date=start_time.date(),
            range_set=True
        )

    def get_bid_price(self, symbol: str, timestamp: Optional[datetime] = None) -> float:
        timestamp = timestamp or PlatformTime.now()
        return self.get_symbol_info(symbol, timestamp).bid_price

    def get_ask_price(self, symbol: str, timestamp: Optional[datetime] = None) -> float:
        timestamp = timestamp or PlatformTime.now()
        return self.get_symbol_info(symbol, timestamp).ask_price

    # 🔒 All calls below use cache only – no runtime mt5 calls

    def is_valid_symbol(self, symbol: str) -> bool:
        return symbol.upper() in self.symbol_info_cache

    def prepare_symbol(self, symbol: str) -> bool:
        return self.is_valid_symbol(symbol)

    def get_min_volume(self, symbol: str) -> float:
        return self._get_mt5_info(symbol).volume_min
    
    def get_max_volume(self, symbol: str) -> float:
        return self._get_mt5_info(symbol).volume_max

    def get_volume_step(self, symbol: str) -> float:
        return self._get_mt5_info(symbol).volume_step

    def get_precision(self, symbol: str) -> int:
        return self._get_mt5_info(symbol).digits

    def get_currency_profit(self, symbol: str) -> str:
        return self._get_mt5_info(symbol).currency_profit

    def get_contract_size(self, symbol: str) -> float:
        return self._get_mt5_info(symbol).trade_contract_size

    def get_tick_size(self, symbol: str) -> float:
        return self._get_mt5_info(symbol).trade_tick_size

    def get_tick_value(self, symbol: str) -> float:
        return self._get_mt5_info(symbol).trade_tick_value

    def get_point_size(self, symbol: str) -> float:
        return self._get_mt5_info(symbol).point

    def get_open_price(self, symbol: str) -> float:
        symbol = symbol.upper()
        df = self.data_by_symbol.get(symbol)
        if df is None or df.empty:
            raise ValueError(f"No data for {symbol}")

        now = PlatformTime.now()
        day_start = now.replace(hour=0, minute=0, second=0, microsecond=0)

        today_data = df.loc[day_start : day_start + timedelta(days=1)]
        if today_data.empty:
            raise ValueError(f"No bars available today for {symbol} (after {day_start})")

        return float(today_data.iloc[0]["open"])