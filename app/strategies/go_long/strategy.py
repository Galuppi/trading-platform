from typing import Any

import logging
from app.base.base_strategy import Strategy
from app.common.system.platform_time import PlatformTime
from app.common.models.model_strategy import StrategyConfig, AssetConfig
from app.common.models.model_trade import TradeRecord
from app.common.config.constants import TRADE_DIRECTION_BUY, TRADE_DIRECTION_SELL
logger = logging.getLogger(__name__)

class GoLongStrategy(Strategy):

    def __init__(self, config: StrategyConfig) -> Any:
        """Perform the defined operation."""
        super().__init__(config=config)

    def initialize(self) -> Any:
        """Perform the defined operation."""
        for asset in self.assets:
            if not self.is_valid_symbol(asset.symbol):
                raise ValueError(f"Symbol '{asset.symbol}' not available or not visible in Market Watch")

    def is_entry_signal(self, asset: AssetConfig) -> str | None:
        """Perform the defined operation."""
        if self.has_reached_max_trades(asset):
            return None
        open_time = PlatformTime.compute_time_from_minutes(asset.open_min or 0)
        if PlatformTime.now().time() >= open_time:
            return TRADE_DIRECTION_BUY
        return None

    def is_exit_signal(self, trade: TradeRecord) -> bool:
        """Perform the defined operation."""
        if trade.strategy != self.strategy_name:
            return False
        for asset in self.assets:
            if asset.symbol == trade.symbol:
                return PlatformTime.minutes_since_midnight() >= (asset.close_min or 0)
        return False