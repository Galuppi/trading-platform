from abc import ABC, abstractmethod
from app.common.models.model_trade import OrderRequest, TradeRecord
from typing import List, Optional


class Account(ABC):
    @abstractmethod
    def get_balance(self) -> float:
        """Return the current account balance."""
        pass

    @abstractmethod
    def set_balance(self, new_balance: float) -> None:
        """Set the account balance to a new value."""
        pass
    
    @abstractmethod
    def set_equity(self, new_equity: float) -> None:
        """Set the account equity to a new value."""
        pass

    @abstractmethod
    def get_equity(self) -> float:
        """Return the current account equity."""
        pass

    @abstractmethod
    def get_commission_per_lot(self) -> float:
        """Return the commission per lot."""
        pass

    @abstractmethod
    def get_free_margin(self, symbol: str) -> float:
        """Return the amount of free margin available."""
        pass

    @abstractmethod
    def get_margin_required(self, order: OrderRequest) -> float:
        """Calculate the margin required to open a position."""
        pass

    @abstractmethod
    def has_sufficient_margin(self, order: OrderRequest) -> bool:
        """Check if there is sufficient margin to open a trade."""
        pass

    @abstractmethod
    def get_account_number(self, backtest_config=None) -> int:
        """Return the trading account number."""
        pass

    @abstractmethod
    def get_account_currency(self) -> str:
        """Return the base currency of the trading account (e.g., USD, EUR, JPY)."""
        pass

    @abstractmethod
    def get_open_tickets(self) -> List[str]:
        """Return open tickets from broker."""
        pass

    @abstractmethod
    def get_closed_tickets(self) -> List[TradeRecord]:
        """Return list of recently closed tickets as TradeRecords from broker history."""
        pass
  
    @abstractmethod
    def get_server_offset_hours(self) -> Optional[float]:
        """Return broker server time offset from internal platform time (in hours)."""
        pass

    @abstractmethod
    def get_server_tick_timestanp(self) -> Optional[int]:
        """Return broker tick timestamp."""
        pass