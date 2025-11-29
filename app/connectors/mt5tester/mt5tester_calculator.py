from typing import Any

from app.base.base_calculator import Calculator
from app.base.base_symbol import Symbol
from app.base.base_account import Account
from app.common.models.model_trade import TradeRecord, ProfitResult
from app.common.models.model_backtest import BacktestConfig
from app.common.config.constants import TRADE_DIRECTION_SELL

class Mt5testerCalculator(Calculator):

    def __init__(self, symbol: Symbol, account: Account, backtester_config: BacktestConfig | None=None) -> Any:
        """Perform the defined operation."""
        self.symbol = symbol
        self.account = account
        self.slippage_per_lot = float(getattr(backtester_config, 'backtest_slippage_per_lot', 0.0) or 0.0)

    def calculate_profit(self, trade: TradeRecord) -> ProfitResult:
        """Perform the defined operation."""
        if trade.entry_price is None or trade.exit_price is None:
            raise ValueError(f'Missing entry or exit price for trade {trade.ticket}')
        price_difference = trade.exit_price - trade.entry_price
        if trade.type.lower() == TRADE_DIRECTION_SELL:
            price_difference = -price_difference
        tick_size = float(self.symbol.get_tick_size(trade.symbol)) or 0.0
        tick_value = float(self.symbol.get_tick_value(trade.symbol)) or 0.0
        if tick_size > 0 and tick_value > 0:
            ticks_moved = price_difference / tick_size
            gross_profit = ticks_moved * tick_value * trade.lot_size
        else:
            contract_size = float(self.symbol.get_contract_size(trade.symbol)) or 1.0
            gross_profit = price_difference * trade.lot_size * contract_size
        commission_per_lot = float(self.account.get_commission_per_lot()) or 0.0
        commission = commission_per_lot * trade.lot_size
        slippage_entry = self.slippage_per_lot * trade.lot_size
        net_profit = gross_profit - commission - slippage_entry
        return ProfitResult(net_profit=round(net_profit, 2), commission=round(commission, 2), slippage_entry=round(slippage_entry, 2))