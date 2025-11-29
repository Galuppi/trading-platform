from typing import Any

from app.base.base_calculator import Calculator

class CTraderCalculator(Calculator):

    def calculate_lot_size_by_capital(self, symbol: str, capital: float) -> float:
        """Perform the defined operation."""
        raise NotImplementedError('CTraderCalculator.calculate_lot_size_by_capital is not implemented.')

    def calculate_lot_size_by_risk(self, symbol: str, capital: float, risk_percent: float) -> float:
        """Perform the defined operation."""
        raise NotImplementedError('CTraderCalculator.calculate_lot_size_by_risk is not implemented.')

    def calculate_stop_loss(self, symbol: str, entry_price: float, sl_points: float) -> float:
        """Perform the defined operation."""
        raise NotImplementedError('CTraderCalculator.calculate_stop_loss is not implemented.')

    def calculate_take_profit(self, symbol: str, entry_price: float, tp_points: float) -> float:
        """Perform the defined operation."""
        raise NotImplementedError('CTraderCalculator.calculate_take_profit is not implemented.')