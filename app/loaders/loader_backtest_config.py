from typing import Any

import os
from app.common.models.model_backtest import BacktestConfig

def str_to_bool(value: str) -> bool:
    """Perform the defined operation."""
    return value.lower() in ('1', 'true', 'yes', 'on')

def load_backtest_config() -> BacktestConfig:
    """Perform the defined operation."""
    return BacktestConfig(backtest_deposit=float(os.getenv('BACKTEST_DEPOSIT', '100000')), backtest_leverage=os.getenv('BACKTEST_LEVERAGE', '1:500'), backtest_currency=os.getenv('BACKTEST_CURRENCY', 'USD'), backtest_date_from=os.getenv('BACKTEST_DATE_FROM', '01-01-2019'), backtest_date_to=os.getenv('BACKTEST_DATE_TO', '01-01-2025'), backtest_timeframe=os.getenv('BACKTEST_TIMEFRAME', 'M1'), backtest_commission_per_lot=float(os.getenv('BACKTEST_COMMISSION_PER_LOT', '7')), backtest_slippage_per_lot=int(os.getenv('BACKTEST_SLIPPAGE_PER_LOT', '10')), backtest_terminal_output=str_to_bool(os.getenv('BACKTEST_TERMINAL_OUTPUT', 'false')), backtest_persist=str_to_bool(os.getenv('BACKTEST_PERSIST', 'false')))