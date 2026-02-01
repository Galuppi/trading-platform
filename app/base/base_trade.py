from abc import ABC, abstractmethod
from app.common.models.model_trade import TradeResult, OrderResult, TradeRecord, OrderRequest
from app.common.services.platform_time import PlatformTime
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
