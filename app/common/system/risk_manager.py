from __future__ import annotations

import logging
from typing import Optional

from app.common.models.model_account import AccountRisk
from app.loaders.loader_account_risk import load_account_risk

logger = logging.getLogger(__name__)


class RiskManager:
    def __init__(self) -> None:
        self._risk: Optional[AccountRisk] = None

    def initialize(self) -> None:
        try:
            self._risk = load_account_risk()
            logger.info(
                "Account risk loaded: stop_loss=%s, take_profit=%s, break_even=%s, profit_level=%s",
                self._risk.account_stop_loss,
                self._risk.account_take_profit,
                self._risk.account_break_even,
                self._risk.account_profit_level,
            )
        except Exception as error:
            logger.error("Failed to load account risk configuration: %s", error)
            self._risk = None

    def get_account_stop_loss(self) -> Optional[float]:
        if self._risk is None:
            return None
        return self._risk.account_stop_loss

    def get_account_risk_enabled(self) -> Optional[bool]:
        if self._risk is None:
            return None
        return self._risk.account_risk_enabled  
    
    def get_account_break_even(self) -> Optional[float]:
        if self._risk is None:
            return None
        return self._risk.account_break_even
    
    def get_account_profit_level(self) -> Optional[float]:
        if self._risk is None:
            return None
        return self._risk.account_profit_level

    def get_account_take_profit(self) -> Optional[float]:
        if self._risk is None:
            return None
        return self._risk.account_take_profit

    def update_account_stop_loss(self, value: float) -> None:
        if self._risk is None:
            logger.warning("Account risk not initialized; stop loss not updated")
            return

        self._risk.account_stop_loss = value
        logger.info("Account stop loss updated — %s", value)

    def update_account_take_profit(self, value: float) -> None:
        if self._risk is None:
            logger.warning("Account risk not initialized; take profit not updated")
            return

        self._risk.account_take_profit = value
        logger.info("Account take profit updated — %s", value)

    def update_account_break_even(self, value: float) -> None:
        if self._risk is None:
            logger.warning("Account risk not initialized; break even not updated")
            return

        self._risk.account_break_even = value
        logger.info("Account break even updated — %s", value)