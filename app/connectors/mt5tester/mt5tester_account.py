from typing import Any

import logging
from typing import List, Optional
from app.base.base_account import Account
from app.common.models.model_trade import OrderRequest, TradeRecord
logger = logging.getLogger(__name__)

class Mt5testerAccount(Account):

    def __init__(self, backtester_config: Any) -> Any:
        """Perform the defined operation."""
        self.balance = float(backtester_config.backtest_deposit)
        self.equity = self.balance
        self.commission_per_lot = float(backtester_config.backtest_commission_per_lot)
        self.account_currency = backtester_config.backtest_currency

    def get_balance(self) -> float:
        """Perform the defined operation."""
        return self.balance

    def get_equity(self) -> float:
        """Perform the defined operation."""
        return self.equity

    def get_commission_per_lot(self) -> float:
        """Perform the defined operation."""
        return self.commission_per_lot

    def get_free_margin(self, symbol: str) -> float:
        """Perform the defined operation."""
        return 0.0

    def get_margin_required(self, order: OrderRequest) -> float:
        """Perform the defined operation."""
        return 0.0

    def has_sufficient_margin(self, order: OrderRequest) -> bool:
        """Perform the defined operation."""
        return True

    def get_account_number(self) -> int:
        """Perform the defined operation."""
        return 99999999

    def get_account_currency(self) -> str:
        """Perform the defined operation."""
        return self.account_currency

    def get_open_tickets(self) -> List[str]:
        """Perform the defined operation."""
        return []

    def get_closed_tickets(self) -> List[TradeRecord]:
        """Perform the defined operation."""
        return []

    def get_server_offset_hours(self) -> Optional[int]:
        """Perform the defined operation."""
        return 0

    def get_server_tick_timestanp(self) -> Optional[int]:
        """Perform the defined operation."""
        return None