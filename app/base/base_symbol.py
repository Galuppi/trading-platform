from typing import Any

from abc import ABC, abstractmethod
from app.common.models.model_symbol import Range
from app.common.config.constants import TIMEFRAME_M1

class Symbol(ABC):

    @abstractmethod

    def get_ask_price(self, symbol: str) -> float:
        """Return the current ask price for the given symbol."""
        pass

    @abstractmethod

    def get_bid_price(self, symbol: str) -> float:
        """Return the current bid price for the given symbol."""
        pass

    @abstractmethod

    def is_valid_symbol(self, symbol: str) -> bool:
        """Check if the given symbol is available and tradable."""
        pass

    @abstractmethod

    def prepare_symbol(self, symbol: str) -> bool:
        """Prepare the symbol for trading (e.g., subscribe or enable it)."""
        pass

    @abstractmethod

    def get_symbol_info(self, symbol: str) -> Any:
        """Retrieve detailed symbol metadata from the broker or platform."""
        pass

    @abstractmethod

    def get_min_volume(self, symbol: str) -> float:
        """Return the minimum tradeable volume for the given symbol."""
        pass

    @abstractmethod

    def get_max_volume(self, symbol: str) -> float:
        """Return the maximum tradeable volume for the given symbol."""
        pass

    @abstractmethod

    def get_volume_step(self, symbol: str) -> float:
        """Return the allowed step size for order volume of the symbol."""
        pass

    @abstractmethod

    def get_precision(self, symbol: str) -> int:
        """Return the number of decimal places for the symbol's price."""
        pass

    @abstractmethod

    def get_contract_size(self, symbol: str) -> float:
        """Return the contract size (units per lot) for the symbol."""
        pass

    @abstractmethod

    def get_tick_size(self, symbol: str) -> float:
        """Return the smallest price increment (tick size) for the symbol."""
        pass

    @abstractmethod

    def get_tick_value(self, symbol: str) -> float:
        """Return the tick value (tick value) per 1 lot for the symbol."""
        pass

    @abstractmethod

    def get_point_size(self, symbol: str) -> float:
        """Return the point size (point size) for the symbol."""
        pass

    @abstractmethod

    def get_currency_profit(self, symbol: str) -> str:
        """Return the profit currency (e.g., USD, JPY, EUR) for the symbol."""
        pass

    @abstractmethod

    def get_high_low_range(self, symbol: str, start_minute: int, end_minute: int, timeframe: str=TIMEFRAME_M1) -> Range:
        """Return the high-low price range for the symbol within the given time window."""
        pass

    @abstractmethod

    def get_point_size(self, symbol: str) -> float:
        """Return the point size for the given symbol."""
        pass