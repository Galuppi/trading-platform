from typing import Any

import json
from pathlib import Path
from datetime import datetime
from typing import Optional
from app.common.config.paths import SUMMARY_PATH
from app.common.config.constants import DATETIME_FORMAT, DATE_FORMAT, TRADE_STATUS_CLOSED
from app.common.models.model_backtest import BacktestConfig, StrategyMetrics
from collections import defaultdict

class BacktestSummary:

    def __init__(self, backtest_config: BacktestConfig) -> Any:
        """Perform the defined operation."""
        self.file_path = SUMMARY_PATH
        self.summary = {}
        self._wall_start: Optional[datetime] = None
        self.backtest_config = backtest_config
        self.total_profit: float = 0.0

    def set_time_range(self, start: datetime, end: datetime) -> Any:
        """Perform the defined operation."""
        self.summary['start_time'] = start.strftime(DATETIME_FORMAT)
        self.summary['end_time'] = end.strftime(DATETIME_FORMAT)

    def set_deposit_info(self, deposit: float, profit: float) -> Any:
        """Perform the defined operation."""
        final_balance = deposit + profit
        self.summary['initial_deposit'] = round(deposit, 2)
        self.summary['total_profit'] = round(profit, 2)
        self.summary['final_balance'] = round(final_balance, 2)

    def set_strategy_metrics(self, trades: list) -> Any:
        """Perform the defined operation."""
        result = defaultdict(StrategyMetrics)
        for trade in trades:
            strategy = trade.strategy
            if trade.status == TRADE_STATUS_CLOSED:
                result[strategy].profit += float(trade.profit or 0.0)
                result[strategy].trades += 1
        self.summary['strategies'] = {k: {'profit': round(v.profit, 2), 'trades': v.trades} for k, v in result.items()}

    def update_total_profit(self, profit: float, trade_date: Optional[str]=None) -> None:
        """Perform the defined operation."""
        self.total_profit += round(profit, 2)
        self.summary['total_profit'] = round(self.total_profit, 2)
        if trade_date:
            self.summary['timestamp'] = trade_date.strftime(DATE_FORMAT)
        else:
            self.summary['timestamp'] = datetime.now().strftime(DATE_FORMAT)

    def get_balance_info(self, initial_deposit: float=100000.0) -> Any:
        """Perform the defined operation."""
        balance = initial_deposit + self.total_profit
        return {'profit': round(self.total_profit, 2), 'balance': round(balance, 2)}

    def get_total_profit(self) -> float:
        """Perform the defined operation."""
        return round(self.total_profit, 2)

    def mark_wall_start(self) -> Any:
        """Perform the defined operation."""
        self._wall_start = datetime.now()
        self.summary['backtest_started_at'] = self._wall_start.strftime(DATETIME_FORMAT)

    def mark_wall_end(self) -> Any:
        """Perform the defined operation."""
        wall_end = datetime.now()
        self.summary['backtest_ended_at'] = wall_end.strftime(DATETIME_FORMAT)
        if self._wall_start is not None:
            total_seconds = int((wall_end - self._wall_start).total_seconds())
            hours = total_seconds // 3600
            minutes = total_seconds % 3600 // 60
            self.summary['backtest_duration'] = f'{hours:02d}:{minutes:02d}'

    def save(self) -> Any:
        """Perform the defined operation."""
        self.file_path.parent.mkdir(parents=True, exist_ok=True)
        with open(self.file_path, 'w', encoding='utf-8') as f:
            json.dump(self.summary, f, indent=4)