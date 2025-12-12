import logging
from app.base.base_account import Account

logger = logging.getLogger(__name__)


class CTradeAccount(Account):
    def get_balance(self) -> float:
        raise NotImplementedError("CTradeAccount.get_balance is not implemented.")

    def get_equity(self) -> float:
        raise NotImplementedError("CTradeAccount.get_equity is not implemented.")

    def get_free_margin(self, symbol: str) -> float:
        raise NotImplementedError("CTradeAccount.get_free_margin is not implemented.")

    def get_margin_required(self, symbol: str, lot_size: float) -> float:
        raise NotImplementedError("CTradeAccount.get_margin_required is not implemented.")

    def has_sufficient_margin(self, symbol: str, lot_size: float) -> bool:
        raise NotImplementedError("CTradeAccount.has_sufficient_margin is not implemented.")

    def get_account_number(self) -> int:
        raise NotImplementedError("CTradeAccount.get_account_number is not implemented.")
