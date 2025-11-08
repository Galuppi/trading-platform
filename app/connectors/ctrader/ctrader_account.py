'''"""This module defines classes related to CTradeAccount."""'''
import logging
from app.base.base_account import Account
logger = logging.getLogger(__name__)

class CTradeAccount(Account):

    def get_balance(self: Any) -> float:
        raise NotImplementedError('CTradeAccount.get_balance is not implemented.')

    def get_equity(self: Any) -> float:
        raise NotImplementedError('CTradeAccount.get_equity is not implemented.')

    def get_free_margin(self: Any, symbol: str) -> float:
        raise NotImplementedError('CTradeAccount.get_free_margin is not implemented.')

    def get_margin_required(self: Any, symbol: str, lot_size: float) -> float:
        raise NotImplementedError('CTradeAccount.get_margin_required is not implemented.')

    def has_sufficient_margin(self: Any, symbol: str, lot_size: float) -> bool:
        raise NotImplementedError('CTradeAccount.has_sufficient_margin is not implemented.')

    def get_account_number(self: Any) -> int:
        raise NotImplementedError('CTradeAccount.get_account_number is not implemented.')
