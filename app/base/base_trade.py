from abc import ABC, abstractmethod
from app.common.models.model_trade import TradeResult, OrderResult, TradeRecord, OrderRequest
from app.common.system.platform_time import PlatformTime
from app.common.config.constants import TRADE_STATUS_OPEN
from typing import Optional


class Trade(ABC):
    @abstractmethod
    def open_position(self, order: OrderRequest) -> OrderResult:
        """Place a new order (market or pending), including SL/TP/comment if present."""
        pass

    @abstractmethod
    def close_position(self, trade: TradeRecord) -> TradeResult:
        """Close an open trade using data from TradeRecord (symbol, lot_size, direction, ticket)."""
        pass

    @abstractmethod
    def modify_position(self, trade: TradeRecord) -> bool:
        """Modifies an open trade using data from TradeRecord (symbol, lot_size, direction, ticket)."""
        pass

    @abstractmethod
    def _open_position(
        self,
        symbol: str,
        size: float,
        direction: str,
        order_type: str,
        sl: float = None,
        tp: float = None,
        price: float = None,
        comment: str = "",
        **kwargs
    ) -> OrderResult:
        """Place a broker-specific order."""
        pass

    @abstractmethod
    def _modify_position(
        self,
        ticket: str,
        sl: Optional[float] = None,
        tp: Optional[float] = None,
        comment: str = "",
        symbol: Optional[str] = None,
        **kwargs
    ) -> TradeResult:
        pass

    