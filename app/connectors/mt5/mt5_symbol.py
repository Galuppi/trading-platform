from typing import Any

import MetaTrader5 as mt5
import logging
from app.common.system.platform_time import PlatformTime
from app.base.base_symbol import Symbol
from app.common.models.model_symbol import Range
from app.common.config.constants import TIMEFRAME_M1, TIMEFRAME_M5, TIMEFRAME_M15, TIMEFRAME_M30, TIMEFRAME_H1, TIMEFRAME_H4, TIMEFRAME_D1
TIMEFRAME_MAP = {TIMEFRAME_M1: mt5.TIMEFRAME_M1, TIMEFRAME_M5: mt5.TIMEFRAME_M5, TIMEFRAME_M15: mt5.TIMEFRAME_M15, TIMEFRAME_M30: mt5.TIMEFRAME_M30, TIMEFRAME_H1: mt5.TIMEFRAME_H1, TIMEFRAME_H4: mt5.TIMEFRAME_H4, TIMEFRAME_D1: mt5.TIMEFRAME_D1}
logger = logging.getLogger(__name__)

class Mt5Symbol(Symbol):

    def get_ask_price(self, symbol: str) -> float:
        """Perform the defined operation."""
        tick = mt5.symbol_info_tick(symbol)
        if tick is None:
            raise ValueError(f'Tick data not available for symbol: {symbol}')
        return tick.ask

    def get_bid_price(self, symbol: str) -> float:
        """Perform the defined operation."""
        tick = mt5.symbol_info_tick(symbol)
        if tick is None:
            raise ValueError(f'Tick data not available for symbol: {symbol}')
        return tick.bid

    def is_valid_symbol(self, symbol: str) -> bool:
        """Perform the defined operation."""
        info = mt5.symbol_info(symbol)
        return info is not None and info.visible

    def prepare_symbol(self, symbol: str) -> bool:
        """Perform the defined operation."""
        return mt5.symbol_select(symbol, True)

    def get_symbol_info(self, symbol: str) -> Any:
        """Perform the defined operation."""
        return mt5.symbol_info(symbol)

    def get_min_volume(self, symbol: str) -> float:
        """Perform the defined operation."""
        info = mt5.symbol_info(symbol)
        if not info:
            raise ValueError(f'Symbol info not found for {symbol}')
        return info.volume_min

    def get_max_volume(self, symbol: str) -> float:
        """Perform the defined operation."""
        info = mt5.symbol_info(symbol)
        if not info:
            raise ValueError(f'Symbol info not found for {symbol}')
        return info.volume_max

    def get_volume_step(self, symbol: str) -> float:
        """Perform the defined operation."""
        info = mt5.symbol_info(symbol)
        if not info:
            raise ValueError(f'Symbol info not found for {symbol}')
        return info.volume_step

    def get_precision(self, symbol: str) -> int:
        """Perform the defined operation."""
        info = mt5.symbol_info(symbol)
        if not info:
            raise ValueError(f'Symbol info not found for {symbol}')
        return info.digits

    def get_contract_size(self, symbol: str) -> float:
        """Perform the defined operation."""
        info = mt5.symbol_info(symbol)
        if not info:
            raise ValueError(f'Symbol info not found for {symbol}')
        return info.trade_contract_size

    def get_tick_size(self, symbol: str) -> float:
        """Perform the defined operation."""
        info = mt5.symbol_info(symbol)
        if not info:
            raise ValueError(f'Symbol info not found for {symbol}')
        return info.trade_tick_size

    def get_point_size(self, symbol: str) -> float:
        """Perform the defined operation."""
        info = mt5.symbol_info(symbol)
        if not info:
            raise ValueError(f'Symbol info not found for {symbol}')
        return info.point

    def get_currency_profit(self, symbol: str) -> str:
        """Perform the defined operation."""
        info = mt5.symbol_info(symbol)
        if not info:
            raise ValueError(f'Symbol info not found for {symbol}')
        return info.currency_profit

    def get_tick_value(self, symbol: str) -> float:
        """Perform the defined operation."""
        info = mt5.symbol_info(symbol)
        if not info:
            raise ValueError(f'Symbol info not found for {symbol}')
        return info.trade_tick_value if info else 0.0

    def get_high_low_range(self, symbol: str, start_minute: int, end_minute: int, timeframe: str=TIMEFRAME_M1) -> Range:
        """Perform the defined operation."""
        if not mt5.initialize():
            raise RuntimeError('MT5 initialization failed')
        now = PlatformTime.now()
        start_time = now.replace(hour=0, minute=0, second=0, microsecond=0) + PlatformTime.timedelta(minutes=start_minute)
        end_time = now.replace(hour=0, minute=0, second=0, microsecond=0) + PlatformTime.timedelta(minutes=end_minute)
        if start_time >= end_time:
            raise ValueError('Start time must be before end time')
        rates = mt5.copy_rates_range(symbol, self._map_timeframe(timeframe), start_time, end_time)
        if rates is None or len(rates) == 0:
            raise RuntimeError(f'Failed to retrieve data for {symbol} from {start_time} to {end_time}')
        highs = [bar['high'] for bar in rates]
        lows = [bar['low'] for bar in rates]
        return Range(symbol=symbol, high=max(highs), low=min(lows), date=PlatformTime.today())

    def _map_timeframe(self, tf: str) -> int:
        """Perform the defined operation."""
        return TIMEFRAME_MAP.get(tf, mt5.TIMEFRAME_M1)