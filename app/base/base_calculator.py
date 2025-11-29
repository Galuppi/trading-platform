from typing import Any

from abc import ABC, abstractmethod
from typing import Optional
from app.common.models.model_trade import OrderRequest, ProfitResult
from app.common.models.model_symbol import Range
from app.common.models.model_strategy import AssetConfig
from app.common.models.model_strategy import StrategyConfig
from app.common.config.constants import TRADE_DIRECTION_BUY

class Calculator(ABC):

    @abstractmethod

    def calculate_profit(self, entry_price: float, exit_price: float, lot_size: float, direction: str) -> ProfitResult:
        """Perform the defined operation."""
        pass

    def calculate_lot_size_by_capital(self, order: OrderRequest) -> float:
        """Perform the defined operation."""
        ask_price = self.symbol.get_ask_price(order.symbol)
        contract_size = self.symbol.get_contract_size(order.symbol)
        if ask_price <= 0 or contract_size <= 0:
            return 0.0
        raw_lot = order.capital / (ask_price * contract_size)
        step = self.symbol.get_volume_step(order.symbol)
        min_volume = self.symbol.get_min_volume(order.symbol)
        max_volume = self.symbol.get_max_volume(order.symbol)
        rounded_lot = self.round_lot_size(raw_lot, step)
        capped_lot = max(min(rounded_lot, max_volume), min_volume)
        return capped_lot

    def calculate_lot_size_by_risk(self, order: OrderRequest, stop_loss_points: int) -> float:
        """Perform the defined operation."""
        if stop_loss_points <= 0:
            return 0.0
        tick_value = self.symbol.get_tick_value(order.symbol)
        contract_size = self.symbol.get_contract_size(order.symbol)
        tick_size = self.symbol.get_tick_size(order.symbol)
        if tick_value <= 0 or contract_size <= 0 or tick_size <= 0:
            return 0.0
        price = self.symbol.get_ask_price(order.symbol) if order.direction == TRADE_DIRECTION_BUY else self.symbol.get_bid_price(order.symbol)
        if price <= 0:
            return 0.0
        risk_amount = order.capital * (order.risk_percent / 100)
        loss_per_lot = stop_loss_points * tick_value
        if loss_per_lot <= 0:
            return 0.0
        raw_lot = risk_amount / (stop_loss_points * tick_value)
        step = self.symbol.get_volume_step(order.symbol)
        min_volume = self.symbol.get_min_volume(order.symbol)
        max_volume = self.symbol.get_max_volume(order.symbol)
        rounded_lot = self.round_lot_size(raw_lot, step)
        capped_lot = max(min(rounded_lot, max_volume), min_volume)
        return capped_lot

    def calculate_stop_loss(self, order: OrderRequest, entry_price: float) -> float:
        """Perform the defined operation."""
        if order.stop_loss_points is None or order.stop_loss_points <= 0:
            return 0.0
        tick_size = self.symbol.get_tick_size(order.symbol)
        digits = self.symbol.get_precision(order.symbol)
        if order.direction == TRADE_DIRECTION_BUY:
            raw_sl = entry_price - order.stop_loss_points * tick_size
        else:
            raw_sl = entry_price + order.stop_loss_points * tick_size
        return self.normalize(raw_sl, digits)

    def calculate_take_profit(self, order: OrderRequest, entry_price: float) -> float:
        """Perform the defined operation."""
        if order.reward_risk_ratio is None or order.reward_risk_ratio <= 0:
            return 0.0
        tp_points = order.stop_loss_points * order.reward_risk_ratio
        tick_size = self.symbol.get_tick_size(order.symbol)
        digits = self.symbol.get_precision(order.symbol)
        if order.direction == TRADE_DIRECTION_BUY:
            raw_tp = entry_price + tp_points * tick_size
        else:
            raw_tp = entry_price - tp_points * tick_size
        return self.normalize(raw_tp, digits)

    def calculate_stop_loss_points(self, order: OrderRequest, range_stop_loss: bool=False, range_open_min: Optional[int]=None, range_close_min: Optional[int]=None) -> int:
        """Perform the defined operation."""
        tick_size = self.symbol.get_tick_size(order.symbol)
        if tick_size <= 0:
            return 0.0
        stop_loss_points = 0.0
        price = self.symbol.get_ask_price(order.symbol) if order.direction == TRADE_DIRECTION_BUY else self.symbol.get_bid_price(order.symbol)
        if price <= 0:
            return 0.0
        if range_stop_loss:
            if range_open_min is None or range_close_min is None:
                return 0.0
            try:
                range_ = self.symbol.get_high_low_range(order.symbol, range_open_min, range_close_min)
            except Exception:
                return 0.0
            if range_.high <= 0 or range_.low <= 0:
                return 0.0
            stop_distance = price - range_.low if order.direction == TRADE_DIRECTION_BUY else range_.high - price
            if stop_distance <= 0:
                return 0.0
            stop_loss_points = stop_distance / tick_size
        else:
            risk_percent = order.risk_percent or 0.0
            if risk_percent <= 0:
                return 0.0
            price_risk_range = price * (risk_percent / 100)
            stop_loss_points = price_risk_range / tick_size
            stop_loss_points_int = int(round(stop_loss_points))
        return max(stop_loss_points_int, 0)

    def recalculate_range(self, range_: Range, price: float) -> Any:
        """Perform the defined operation."""
        if range_.range_set:
            return
        range_.high = max(range_.high, price)
        range_.low = min(range_.low, price)

    def calculate_allocated_capital(self, config: StrategyConfig, asset: AssetConfig) -> float:
        """Perform the defined operation."""
        if not asset.percent_of_capital:
            return 0.0
        return config.total_strategy_capital * (asset.percent_of_capital / 100)

    def round_lot_size(self, raw_lot: float, step: float) -> float:
        """Perform the defined operation."""
        if step == 1:
            precision = 0
        elif step >= 0.1:
            precision = 1
        else:
            precision = 2
        return round(raw_lot, precision)

    def normalize(self, value: float, digits: int) -> float:
        """Perform the defined operation."""
        if value is None:
            return None
        if digits < 0:
            raise ValueError('Digits must be non-negative')
        return round(value, digits)