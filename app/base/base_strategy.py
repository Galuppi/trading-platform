from typing import Any

from abc import ABC, abstractmethod
from typing import Optional
from app.base.base_symbol import Symbol
from app.base.base_account import Account
from app.base.base_trade import Trade
from app.base.base_calculator import Calculator
from app.base.base_connector import Connector
from app.common.models.model_trade import TradeRecord
from app.common.models.model_strategy import StrategyConfig, AssetConfig
from app.common.models.model_trade import TradeRecord, OrderRequest
from app.common.system.platform_time import PlatformTime
from app.common.config.constants import TRADE_DIRECTION_BUY, TRADE_DIRECTION_SELL, TRADE_STATUS_OPEN, TRADE_STATUS_CLOSED
from app.loaders.loader_traderecord import create_trade_record
from app.loaders.loader_orderrequest import build_order_request

class Strategy(ABC):

    def __init__(self, config: StrategyConfig) -> Any:
        """Initialize the strategy with configuration."""
        self.config: StrategyConfig = config
        self.assets: list[AssetConfig] = config.assets
        self.holidays: list[str] = []
        self.connector: Optional[Connector] = None
        self.account: Optional[Account] = None
        self.symbol: Optional[Symbol] = None
        self.trade: Optional[Trade] = None
        self.calculator: Optional[Calculator] = None
        self.state_manager = None

    def attach_services(self, *, connector: Connector, account: Account, symbol: Symbol, trader: Trade, calculator: Calculator, state_manager) -> Any:
        """Attach external services required for strategy execution."""
        self.connector = connector
        self.account = account
        self.symbol = symbol
        self.trade = trader
        self.calculator = calculator
        self.state_manager = state_manager

    def set_holidays(self, holidays: list[str]) -> Any:
        """Set the list of holiday dates (ISO format) to avoid trading."""
        self.holidays = holidays

    def is_valid_symbol(self, symbol: str) -> bool:
        """Check if the symbol is valid and can be prepared."""
        return self.symbol.prepare_symbol(symbol) if self.symbol else False

    def is_holiday(self) -> bool:
        """Return True if today is a defined trading holiday."""
        return PlatformTime.today() in self.holidays

    def is_market_open(self) -> bool:
        """Check if the market is currently open based on strategy config."""
        if not self.config.market_hours:
            return False
        sessions = self.config.market_hours.sessions
        current_day = PlatformTime.now().strftime('%A')
        return PlatformTime.is_within_market_hours(current_day, sessions)

    def prepare_order(self, asset: AssetConfig, direction: str) -> OrderRequest:
        """Build an order request with calculated lot size based on strategy rules."""
        return build_order_request(asset=asset, direction=direction, config=self.config, calculator=self.calculator, strategy_name=self.strategy_name, strategy_display_name=self.strategy_display_name)

    def is_entry_allowed(self, asset: AssetConfig, order: OrderRequest) -> bool:
        """Return True if a new trade is allowed under strategy and asset constraints."""
        if self.is_holiday() or not self.is_market_open():
            return False
        direction = order.direction
        today = PlatformTime.now().date()
        trades_today = [t for t in self.state_manager.get_all_trades() if t.symbol == asset.symbol and t.strategy == self.strategy_name and (PlatformTime.parse_platform_timestamp(t.timestamp).date() == today)]
        if asset.max_total_trades is not None:
            if len(trades_today) >= asset.max_total_trades:
                return False
        elif direction == TRADE_DIRECTION_BUY:
            if asset.max_buy_trades == 0:
                return False
            if asset.max_buy_trades is not None:
                trades_same = [t for t in trades_today if t.type == TRADE_DIRECTION_BUY]
                if len(trades_same) >= asset.max_buy_trades:
                    return False
        elif direction == TRADE_DIRECTION_SELL:
            if asset.max_sell_trades == 0:
                return False
            if asset.max_sell_trades is not None:
                trades_same = [t for t in trades_today if t.type == TRADE_DIRECTION_SELL]
                if len(trades_same) >= asset.max_sell_trades:
                    return False
        else:
            return False
        return self.account.has_sufficient_margin(order)

    def is_exit_allowed(self, trade: TradeRecord) -> bool:
        """Check if conditions allow this trade to be closed."""
        return not self.is_holiday() and self.is_market_open()

    def execute_entry(self, order: OrderRequest) -> Any:
        """Send a market order and record the trade if accepted."""
        if order.lot_size <= 0:
            return
        entry_price = self.symbol.get_ask_price(order.symbol) if order.direction == TRADE_DIRECTION_BUY else self.symbol.get_bid_price(order.symbol)
        order.stop_loss = self.calculator.calculate_stop_loss(order, entry_price)
        order.take_profit = self.calculator.calculate_take_profit(order, entry_price)
        result = self.trade.open_position(order)
        if result.accepted:
            trade = create_trade_record(result=result, order=order, entry_price=entry_price, strategy_name=self.strategy_name)
            self.state_manager.add_trade(trade)

    def set_range(self) -> Any:
        """Optional hook to update internal strategy state per tick/cycle."""
        pass

    def execute_exit(self, trade: TradeRecord, stopped: bool=False) -> None:
        """Send a market order and record the trade if accepted."""
        result = self.trade.close_position(trade)
        if not result or not result.accepted:
            return
        if stopped:
            trade.comment = 'SL/TP hit'
            trade.exit_price = trade.stop_loss
        else:
            trade.comment = 'Closed by signal'
        self.state_manager.add_trade(trade)

    def manage_entry(self, trade: TradeRecord) -> None:
        """Strategy-level trade management hook."""
        changed = self.trade.modify_position(trade)
        if changed:
            self.state_manager.add_trade(trade)

    def finalize(self) -> Any:
        """Hook for cleanup or final adjustments before shutdown."""
        pass

    def has_reached_max_trades(self, asset: AssetConfig) -> bool:
        """Return True if this strategy has reached its max trades for the asset today."""
        open_trades = self.state_manager.get_open_trades(symbol=asset.symbol, strategy=self.strategy_name, date=PlatformTime.today())
        max_total = asset.max_total_trades or float('inf')
        max_direction = {TRADE_DIRECTION_BUY: asset.max_buy_trades or 0, TRADE_DIRECTION_SELL: asset.max_sell_trades or 0}
        count_total = len(open_trades)
        count_dir = sum((1 for t in open_trades if t.type in max_direction))
        if count_total >= max_total:
            return True
        if any((count_dir >= max_direction.get(t.type, 0) for t in open_trades)):
            return True
        return False

    def is_sl_tp_hit(self, trade: TradeRecord) -> bool:
        """Perform the defined operation."""
        if trade.status != TRADE_STATUS_OPEN:
            return False
        ask = self.symbol.get_ask_price(trade.symbol)
        bid = self.symbol.get_bid_price(trade.symbol)
        stop_loss = trade.stop_loss or 0
        take_profit = trade.take_profit or 0
        if trade.type == TRADE_DIRECTION_BUY:
            if stop_loss > 0 and bid <= stop_loss:
                return True
            if take_profit > 0 and bid >= take_profit:
                return True
        elif trade.type == TRADE_DIRECTION_SELL:
            if stop_loss > 0 and ask >= stop_loss:
                return True
            if take_profit > 0 and ask <= take_profit:
                return True
        return False

    @property

    def strategy_name(self) -> str:
        """Return the lowercase class name as the strategy identifier."""
        return self.__class__.__name__.lower()

    @property

    def strategy_display_name(self) -> str:
        """Return the configured strategy label or fallback to strategy name."""
        return self.config.display_name or self.strategy_name

    @abstractmethod

    def initialize(self) -> Any:
        """Initialize internal state and prepare for execution."""
        pass

    @abstractmethod

    def is_entry_signal(self, asset: AssetConfig) -> Optional[str]:
        """Check if market conditions trigger an entry signal."""
        pass

    @abstractmethod

    def is_exit_signal(self, trade: TradeRecord) -> bool:
        """Check if market conditions trigger an exit signal for a trade."""
        pass