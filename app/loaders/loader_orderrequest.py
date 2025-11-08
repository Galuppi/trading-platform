'''"""This module provides functions including build_order_request."""'''
from app.common.models.model_trade import OrderRequest

def build_order_request(asset: Any, direction: str, config: Any, calculator: Any, strategy_name: str, strategy_display_name: str) -> OrderRequest:
    allocated_capital = calculator.calculate_allocated_capital(config, asset)
    order = OrderRequest(symbol=asset.symbol, direction=direction, lot_size=0.0, capital=allocated_capital, strategy_name=strategy_name, stop_loss=None, risk_percent=asset.risk_percent or 0, comment=strategy_display_name)
    stop_loss_points = calculator.calculate_stop_loss_points(order, asset.range_stop_loss, asset.range_open_min, asset.range_close_min)
    order.stop_loss_points = stop_loss_points
    if config.positioning == 'risk':
        order.lot_size = calculator.calculate_lot_size_by_risk(order, stop_loss_points)
    else:
        order.lot_size = calculator.calculate_lot_size_by_capital(order)
    return order
