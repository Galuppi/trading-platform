from typing import Any

from dataclasses import dataclass
from typing import Optional

@dataclass
class BacktestConfig:
    backtest_deposit: Optional[float]
    backtest_leverage: Optional[str]
    backtest_currency: Optional[str]
    backtest_date_from: Optional[str]
    backtest_date_to: Optional[str]
    backtest_timeframe: Optional[str]
    backtest_commission_per_lot: Optional[float]
    backtest_slippage_per_lot: Optional[int]
    backtest_terminal_output: Optional[bool]
    backtest_persist: Optional[bool]

@dataclass
class StrategyMetrics:
    profit: float = 0.0
    trades: int = 0