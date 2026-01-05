import logging

from app.base.base_strategy import Strategy
from app.common.models.model_strategy import StrategyConfig, AssetConfig
from app.common.models.model_trade import TradeRecord
from app.common.models.model_symbol import Range
from app.common.system.platform_time import PlatformTime
from app.common.config.constants import TRADE_DIRECTION_BUY, TRADE_DIRECTION_SELL

logger = logging.getLogger(__name__)


class BreakOutStrategy(Strategy):
    def __init__(self, config: StrategyConfig):
        super().__init__(config=config)
        self.range_by_symbol: dict[str, Range] = {}

    def initialize(self):
        for asset in self.assets:
            if not self.is_valid_symbol(asset.symbol):
                raise ValueError(
                    f"Symbol '{asset.symbol}' not available or not visible in Market Watch"
                )

            self.range_by_symbol[asset.symbol] = Range(
                symbol=asset.symbol,
                high=float("-inf"),
                low=float("inf"),
                date=PlatformTime.today(),
                range_set=False
            )

    def set_range(self):
        now_min = PlatformTime.minutes_since_midnight()

        for asset in self.assets:
            range_ = self.range_by_symbol.get(asset.symbol)

            if not range_ or range_.date != PlatformTime.today():
                self.range_by_symbol[asset.symbol] = Range(
                    symbol=asset.symbol,
                    high=float("-inf"),
                    low=float("inf"),
                    date=PlatformTime.today(),
                    range_set=False
                )
                range_ = self.range_by_symbol[asset.symbol]

            if range_.range_set or now_min < (asset.range_close_min or 0):
                continue

            try:
                hist_range = self.symbol.get_high_low_range(
                    symbol=asset.symbol,
                    start_minute=asset.range_open_min or 0,
                    end_minute=asset.range_close_min or 0
                )
                range_.high = hist_range.high
                range_.low = hist_range.low
                range_.range_set = True
                
            except Exception as e:
                logger.warning(
                    f"[{self.strategy_name}] Failed to calculate range for {asset.symbol}: {e}"
                )

    def is_entry_signal(self, asset: AssetConfig) -> str | None:
        if self.state_manager.get_target_reached():
            return None
        if self.has_reached_max_trades(asset):
            return None

        now_min = PlatformTime.minutes_since_midnight()
        if now_min < (asset.open_min or 0):
            return None

        range_ = self.range_by_symbol.get(asset.symbol)
        if not range_ or not range_.range_set:
            return None

        price = self.symbol.get_ask_price(asset.symbol)
        if price <= 0:
            return None

        if asset.range_size_restricted is not None and asset.range_size_restricted:
            range_size_monetary = range_.high - range_.low
            min_allowed_range = 0.001 * price
            max_allowed_range = 0.008 * price
            if not (min_allowed_range <= range_size_monetary <= max_allowed_range):
                #debug
                #logger.info(f"Range size for {asset.symbol} is out of allowed bounds: {range_size_monetary:.5f} (allowed: {min_allowed_range:.5f} - {max_allowed_range:.5f})") 
                return None

        if price > range_.high:
            return TRADE_DIRECTION_BUY
        elif price < range_.low:
            return TRADE_DIRECTION_SELL
        return None

    def is_exit_signal(self, trade: TradeRecord) -> bool:
        if self.state_manager.get_target_reached():
            return True
        
        if trade.strategy != self.strategy_name:
            return False
         
        for asset in self.assets:
            if asset.symbol == trade.symbol:
                return PlatformTime.minutes_since_midnight() >= (asset.close_min or 0)
        return False
    