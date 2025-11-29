from typing import Any

import csv
import logging
from pathlib import Path
from datetime import datetime
from typing import Optional
from app.base.base_trade import Trade
from app.base.base_calculator import Calculator
from app.common.config.paths import RESULT_PATH
from app.common.models.model_trade import OrderRequest, OrderResult, TradeRecord, TradeResult, ProfitResult
from app.common.system.platform_time import PlatformTime
from app.common.system.backtest_summary import BacktestSummary
from app.common.config.constants import TRADE_DIRECTION_BUY, TRADE_STATUS_CLOSED, DATETIME_FORMAT
logger = logging.getLogger(__name__)

class Mt5testerTrade(Trade):

    def __init__(self, symbol: Any, calculator: Calculator, summary_writer: BacktestSummary) -> Any:
        """Perform the defined operation."""
        self.symbol = symbol
        self.calculator = calculator
        self.summary_writer = summary_writer
        self.result_file_path = Path(RESULT_PATH) / f"results_{datetime.now().strftime('%Y%m%d%H%M')}.csv"
        self.result_file_path.parent.mkdir(parents=True, exist_ok=True)
        self._wrote_header = False
        if self.calculator is None:
            print('[ERROR] Calculator is None in Mt5testerTrade constructor!')

    def open_position(self, order: OrderRequest) -> OrderResult:
        """Perform the defined operation."""
        if not order.price or order.price <= 0:
            direction = order.direction.lower()
            if direction == TRADE_DIRECTION_BUY:
                market_price = self.symbol.get_ask_price(order.symbol)
            else:
                market_price = self.symbol.get_bid_price(order.symbol)
            if market_price is None or market_price <= 0:
                return OrderResult(symbol=order.symbol, lot_size=order.lot_size, accepted=False, order_id='', retcode=10001, comment='Rejected: No historical data available for price', deal=None, request={})
            order.price = market_price
        trade_id = f'sim-{order.symbol}-{order.direction}-{PlatformTime.now().isoformat()}'
        order_result = OrderResult(symbol=order.symbol, lot_size=order.lot_size, accepted=True, order_id=trade_id, retcode=-1, comment='Simulated order', deal=PlatformTime.now().isoformat(), request={'entry_price': order.price})
        self._log_order(order, trade_id)
        return order_result

    def close_position(self, trade: TradeRecord) -> TradeResult:
        """Perform the defined operation."""
        if trade.exit_price is None:
            direction = trade.type.lower()
            price = self.symbol.get_bid_price(trade.symbol) if direction == TRADE_DIRECTION_BUY else self.symbol.get_ask_price(trade.symbol)
            if price is None or price <= 0:
                return TradeResult(symbol=trade.symbol, lot_size=trade.lot_size, accepted=False, ticket=trade.ticket, retcode=-1, close_price=None, profit=0.0, closed=False, comment='Rejected: No market price at close time')
            trade.exit_price = price
        result = self._calculate_profit(trade)
        trade.exit_time = PlatformTime.now().strftime(DATETIME_FORMAT)
        trade.status = TRADE_STATUS_CLOSED
        trade.profit = result.net_profit
        trade.commission = result.commission
        trade.slippage_entry = result.slippage_entry
        if not trade.comment:
            trade.comment = 'Simulated close'
        if self.summary_writer:
            try:
                self.summary_writer.update_total_profit(trade.profit, PlatformTime.now())
            except Exception as e:
                print(f'[WARNING] Failed to update backtest summary: {e}')
        self._log_close(trade)
        return TradeResult(symbol=trade.symbol, lot_size=trade.lot_size, accepted=True, ticket=trade.ticket, retcode=10009, close_price=trade.exit_price, profit=trade.profit, closed=True, comment=trade.comment)

    def _open_position(self, *args, **kwargs) -> Any:
        """Perform the defined operation."""
        return self.open_position(OrderRequest(**kwargs))

    def _log_order(self, order: OrderRequest, trade_id: str) -> Any:
        """Perform the defined operation."""
        pass

    def _log_close(self, trade: TradeRecord) -> Any:
        """Perform the defined operation."""
        if trade.exit_price is None:
            return
        is_new_file = not self.result_file_path.exists() and (not self._wrote_header)
        with open(self.result_file_path, mode='a', newline='') as f:
            writer = csv.writer(f)
            if is_new_file:
                writer.writerow(['Time', 'Strategy', 'Type', 'Volume', 'Symbol', 'Entry Price', 'SL', 'TP', 'Close Time', 'Exit Price', 'Commission', 'Swap', 'Slippage', 'Net Profit', 'Comment'])
                self._wrote_header = True
            writer.writerow([PlatformTime.to_mt_time_format(trade.timestamp), trade.strategy.capitalize(), trade.type.capitalize(), trade.lot_size, trade.symbol, trade.entry_price, trade.stop_loss, trade.take_profit, PlatformTime.to_mt_time_format(trade.exit_time), trade.exit_price, trade.commission, 0.0, trade.slippage_entry, trade.profit, trade.comment])

    def _calculate_profit(self, trade: TradeRecord) -> ProfitResult:
        """Perform the defined operation."""
        return self.calculator.calculate_profit(trade)

    def _modify_position(self, ticket: str, sl: Optional[float]=None, tp: Optional[float]=None, comment: str='', symbol: Optional[str]=None, **kwargs) -> TradeResult:
        """Perform the defined operation."""
        raise NotImplementedError

    def modify_position(self, trade: TradeRecord) -> bool:
        """Perform the defined operation."""
        return False