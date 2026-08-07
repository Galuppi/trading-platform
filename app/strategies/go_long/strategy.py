"""Simple long-only strategy that enters a single directional trade per session."""

import logging

from typing import Optional

from app.base.base_strategy import Strategy

from app.common.services.platform_time import PlatformTime
from app.common.models.model_strategy import StrategyConfig, AssetConfig
from app.common.models.model_trade import TradeRecord
from app.common.config.constants import TRADE_DIRECTION_BUY, TRADE_DIRECTION_SELL

logger = logging.getLogger(__name__)


class GoLongStrategy(Strategy):
    """Simple long-only strategy that enters a single directional trade per session."""

    def __init__(self, config: StrategyConfig):
        super().__init__(config=config)

    def initialize(self) -> None:
        for asset in self.assets:
            if not self.is_valid_symbol(asset.symbol):
                raise ValueError(
                    f"Symbol '{asset.symbol}' not available or not visible in Market Watch"
                )

    def is_entry_signal(self, asset: AssetConfig) -> Optional[str]:
        if self.state_manager.get_target_reached():
            return None

        if self.state_manager.get_weekly_profit_reached():
            return None

        if self.has_reached_max_trades(asset):
            return None

        open_time = PlatformTime.compute_time_from_minutes(asset.open_min or 0)
        if PlatformTime.now().time() >= open_time:
            return TRADE_DIRECTION_BUY
        return None

    def is_exit_signal(self, trade: TradeRecord, asset_config: AssetConfig) -> bool:
        if self.state_manager.get_target_reached():
            return True

        if self.state_manager.get_weekly_profit_reached():
            return True

        if trade.strategy != self.strategy_name:
            return False

        return PlatformTime.minutes_since_midnight() >= (asset_config.close_min or 0)
