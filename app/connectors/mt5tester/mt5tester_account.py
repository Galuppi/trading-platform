'''"""This module defines classes related to Mt5testerAccount."""'''
import logging
from typing import List, Optional
from app.base.base_account import Account
from app.common.models.model_trade import OrderRequest, TradeRecord
logger = logging.getLogger(__name__)

class Mt5testerAccount(Account):

    def __init__(self: Any, backtester_config: Any) -> Any:
        self.balance = float(backtester_config.backtest_deposit)
        self.equity = self.balance
        self.commission_per_lot = float(backtester_config.backtest_commission_per_lot)
        self.account_currency = backtester_config.backtest_currency

    def get_balance(self: Any) -> float:
        return self.balance

    def get_equity(self: Any) -> float:
        return self.equity

    def get_commission_per_lot(self: Any) -> float:
        return self.commission_per_lot

    def get_free_margin(self: Any, symbol: str) -> float:
        return 0.0

    def get_margin_required(self: Any, order: OrderRequest) -> float:
        return 0.0

    def has_sufficient_margin(self: Any, order: OrderRequest) -> bool:
        return True

    def get_account_number(self: Any) -> int:
        return 99999999

    def get_account_currency(self: Any) -> str:
        return self.account_currency

    def get_open_tickets(self: Any) -> List[str]:
        return []

    def get_closed_tickets(self: Any) -> List[TradeRecord]:
        return []

    def get_server_offset_hours(self: Any) -> Optional[int]:
        return 0

    def get_server_tick_timestanp(self: Any) -> Optional[int]:
        return None
