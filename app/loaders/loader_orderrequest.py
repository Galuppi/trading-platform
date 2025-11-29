from typing import Any

from app.common.models.model_trade import OrderRequest
from app.common.config.constants import POSITIONING_RISK

def build_order_request(asset: Any, direction: str, config: Any, calculator: Any, strategy_name: str, strategy_display_name: str) -> OrderRequest:
    """Perform the defined operation."""
    allocated_capital = calculator.calculate_allocated_capital(config, asset)
    order = OrderRequest(symbol=asset.symbol, direction=direction, lot_size=0.0, capital=allocated_capital, strategy_name=strategy_name, stop_loss=None, risk_percent=asset.risk_percent or 0, comment=strategy_display_name, reward_risk_ratio=asset.reward_risk_ratio or 0)
    stop_loss_points = calculator.calculate_stop_loss_points(order, asset.range_stop_loss, asset.range_open_min, asset.range_close_min)
    order.stop_loss_points = stop_loss_points
    if config.positioning == POSITIONING_RISK:
        order.lot_size = calculator.calculate_lot_size_by_risk(order, stop_loss_points)
    else:
        order.lot_size = calculator.calculate_lot_size_by_capital(order)
    return order