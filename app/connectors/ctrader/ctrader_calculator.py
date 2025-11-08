'''"""This module defines classes related to CTraderCalculator."""'''
from app.base.base_calculator import Calculator

class CTraderCalculator(Calculator):

    def calculate_lot_size_by_capital(self: Any, symbol: str, capital: float) -> float:
        raise NotImplementedError('CTraderCalculator.calculate_lot_size_by_capital is not implemented.')

    def calculate_lot_size_by_risk(self: Any, symbol: str, capital: float, risk_percent: float) -> float:
        raise NotImplementedError('CTraderCalculator.calculate_lot_size_by_risk is not implemented.')

    def calculate_stop_loss(self: Any, symbol: str, entry_price: float, sl_points: float) -> float:
        raise NotImplementedError('CTraderCalculator.calculate_stop_loss is not implemented.')

    def calculate_take_profit(self: Any, symbol: str, entry_price: float, tp_points: float) -> float:
        raise NotImplementedError('CTraderCalculator.calculate_take_profit is not implemented.')
