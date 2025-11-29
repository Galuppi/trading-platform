from typing import Any

import logging
from app.base.base_calculator import Calculator
from app.base.base_symbol import Symbol
from app.base.base_account import Account
from app.common.models.model_trade import ProfitResult
logger = logging.getLogger(__name__)

class Mt5Calculator(Calculator):

    def __init__(self, symbol: Symbol, account: Account) -> Any:
        """Perform the defined operation."""
        self.symbol = symbol
        self.account = account

    def calculate_profit(self, entry_price: Any, exit_price: Any, lot_size: Any, direction: Any) -> ProfitResult:
        """Perform the defined operation."""
        return ProfitResult()