from typing import Any

import logging
from app.base.base_strategy import Strategy
from app.common.models.model_strategy import StrategyConfig, AssetConfig
from app.common.models.model_trade import TradeRecord
from app.common.models.model_symbol import Range
from app.common.system.platform_time import PlatformTime
from app.common.config.constants import TRADE_DIRECTION_BUY, TRADE_DIRECTION_SELL
logger = logging.getLogger(__name__)

class CryptoStrategy(Strategy):

    def __init__(self, config: StrategyConfig) -> Any:
        """Perform the defined operation."""
        super().__init__(config=config)
        self.range_by_symbol: dict[str, Range] = {}

    def initialize(self) -> Any:
        """Perform the defined operation."""
        for asset in self.assets:
            if not self.is_valid_symbol(asset.symbol):
                raise ValueError(f"Symbol '{asset.symbol}' not available or not visible in Market Watch")
            self.range_by_symbol[asset.symbol] = Range(symbol=asset.symbol, high=float('-inf'), low=float('inf'), date=PlatformTime.today(), range_set=False)

    def set_range(self) -> Any:
        """Perform the defined operation."""
        now_min = PlatformTime.minutes_since_midnight()
        for asset in self.assets:
            range_ = self.range_by_symbol.get(asset.symbol)
            if not range_ or range_.date != PlatformTime.today():
                self.range_by_symbol[asset.symbol] = Range(symbol=asset.symbol, high=float('-inf'), low=float('inf'), date=PlatformTime.today(), range_set=False)
                range_ = self.range_by_symbol[asset.symbol]
            if range_.range_set or now_min < (asset.range_close_min or 0):
                continue
            try:
                hist_range = self.symbol.get_high_low_range(symbol=asset.symbol, start_minute=asset.range_open_min or 0, end_minute=asset.range_close_min or 0)
                range_.high = hist_range.high
                range_.low = hist_range.low
                range_.range_set = True
            except Exception as e:
                logger.warning(f'[{self.strategy_name}] Failed to calculate range for {asset.symbol}: {e}')

    def is_entry_signal(self, asset: AssetConfig) -> str | None:
        """Perform the defined operation."""
        if self.has_reached_max_trades(asset):
            return None
        now_min = PlatformTime.minutes_since_midnight()
        if now_min < (asset.open_min or 0):
            return None
        last_trade = self.state_manager.get_last_trade(asset.symbol)
        if last_trade is not None:
            last_trade_time = PlatformTime.parse_datetime_str(last_trade.timestamp)
            time_since_last_trade = PlatformTime.now() - last_trade_time
            if time_since_last_trade < PlatformTime.timedelta(minutes=asset.trade_cooldown_minutes or 0):
                return None
        last_closed_trade = self.state_manager.get_last_closed_trade(asset.symbol)
        if last_closed_trade is not None:
            if last_closed_trade.exit_time is None:
                logger.warning(f'Last closed trade ({last_closed_trade.id}) has no exit_time — skipping cooldown check')
            else:
                last_closed_trade_profit = last_closed_trade.profit or 0.0
                last_closed_trade_exit_time = PlatformTime.parse_datetime_str(last_closed_trade.exit_time)
                time_since_last_close = PlatformTime.now() - last_closed_trade_exit_time
                if last_closed_trade_profit < 0.0 and time_since_last_close < PlatformTime.timedelta(minutes=240):
                    return None
        range_ = self.range_by_symbol.get(asset.symbol)
        if not range_ or not range_.range_set:
            return None
        price = self.symbol.get_ask_price(asset.symbol)
        if price > range_.high:
            return TRADE_DIRECTION_BUY
        elif price < range_.low:
            return TRADE_DIRECTION_SELL
        return None

    def is_exit_signal(self, trade: TradeRecord) -> bool:
        """Perform the defined operation."""
        if trade.strategy != self.strategy_name:
            return False
        for asset in self.assets:
            if asset.symbol == trade.symbol:
                return PlatformTime.minutes_since_midnight() >= (asset.close_min or 0)
        return False