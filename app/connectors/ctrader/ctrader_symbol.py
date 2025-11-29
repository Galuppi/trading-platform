from typing import Any

from app.base.base_symbol import Symbol
from typing import Tuple

class CTraderSymbol(Symbol):

    def get_ask_price(self, symbol: str) -> float:
        """Perform the defined operation."""
        raise NotImplementedError('get_ask_price not implemented for CTrader')

    def get_bid_price(self, symbol: str) -> float:
        """Perform the defined operation."""
        raise NotImplementedError('get_bid_price not implemented for CTrader')

    def is_valid_symbol(self, symbol: str) -> bool:
        """Perform the defined operation."""
        raise NotImplementedError('is_valid_symbol not implemented for CTrader')

    def prepare_symbol(self, symbol: str) -> bool:
        """Perform the defined operation."""
        raise NotImplementedError('prepare_symbol not implemented for CTrader')

    def get_symbol_info(self, symbol: str) -> Any:
        """Perform the defined operation."""
        raise NotImplementedError('get_symbol_info not implemented for CTrader')

    def get_min_volume(self, symbol: str) -> float:
        """Perform the defined operation."""
        raise NotImplementedError('get_min_volume not implemented for CTrader')

    def get_volume_step(self, symbol: str) -> float:
        """Perform the defined operation."""
        raise NotImplementedError('get_volume_step not implemented for CTrader')

    def get_precision(self, symbol: str) -> float:
        """Perform the defined operation."""
        raise NotImplementedError('get_precision not implemented for CTrader')

    def get_high_low_range(self, symbol: str, start_minute: int, end_minute: int, timeframe: str=TIMEFRAME_M1) -> Tuple[float, float]:
        """Perform the defined operation."""
        raise NotImplementedError('get_high_low_range not yet implemented for MT5')