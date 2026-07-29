"""Manages account-level risk thresholds (take profit, stop loss, break-even)."""

from __future__ import annotations

import logging
from typing import Optional

from app.common.models.model_account import AccountRisk
from app.common.config.loaders.loader_account_risk import load_account_risk

logger = logging.getLogger(__name__)


class RiskManager:
    """Manages account-level risk thresholds (take profit, stop loss, break-even)."""
    def __init__(self) -> None:
        self._risk: Optional[AccountRisk] = None

    def initialize(self) -> None:
        try:
            self._risk = load_account_risk()
            logger.info(
                "Account risk loaded: stop_loss=%s, take_profit=%s, break_even=%s, profit_level=%s, take_profit_week=%s",
                self._risk.stop_loss,
                self._risk.take_profit,
                self._risk.break_even,
                self._risk.profit_level,
                self._risk.take_profit_week,
            )
        except Exception as error:
            logger.error("Failed to load account risk configuration: %s", error)
            self._risk = None

    @property
    def stop_loss(self) -> Optional[float]:
        return self._risk.stop_loss if self._risk else None

    @stop_loss.setter
    def stop_loss(self, value: float) -> None:
        if self._risk is None:
            logger.warning("Account risk not initialized; stop loss not updated")
            return
        self._risk.stop_loss = value
        logger.info("Account stop loss updated — %s", value)

    @property
    def enabled(self) -> Optional[bool]:
        return self._risk.enabled if self._risk else None

    @property
    def break_even(self) -> Optional[float]:
        return self._risk.break_even if self._risk else None

    @break_even.setter
    def break_even(self, value: float) -> None:
        if self._risk is None:
            logger.warning("Account risk not initialized; break even not updated")
            return
        self._risk.break_even = value
        logger.info("Account break even updated — %s", value)

    @property
    def profit_level(self) -> Optional[float]:
        return self._risk.profit_level if self._risk else None

    @property
    def take_profit(self) -> Optional[float]:
        return self._risk.take_profit if self._risk else None

    @take_profit.setter
    def take_profit(self, value: float) -> None:
        if self._risk is None:
            logger.warning("Account risk not initialized; take profit not updated")
            return
        self._risk.take_profit = value
        logger.info("Account take profit updated — %s", value)

    @property
    def take_profit_week(self) -> Optional[float]:
        return self._risk.take_profit_week if self._risk else None
