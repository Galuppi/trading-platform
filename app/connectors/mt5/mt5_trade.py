from typing import Any

import logging
import MetaTrader5 as mt5
from typing import Optional
from app.base.base_trade import Trade
from app.common.config.constants import TRADE_DIRECTION_BUY, TRADE_DIRECTION_SELL, TRADE_STATUS_CLOSED, DATETIME_FORMAT
from app.common.models.model_trade import OrderRequest, TradeRecord, OrderResult, TradeResult
from app.common.system.platform_time import PlatformTime
logger = logging.getLogger(__name__)

class Mt5Trade(Trade):

    def open_position(self, order: OrderRequest) -> OrderResult:
        """Perform the defined operation."""
        logger.info(f'Placing order — Symbol: {order.symbol}, Lot Size: {order.lot_size}, Direction: {order.direction}, SL: {order.stop_loss}, TP: {order.take_profit}, Comment: {order.comment}')
        return self._open_position(symbol=order.symbol, size=order.lot_size, direction=order.direction, sl=order.stop_loss, tp=order.take_profit, comment=order.comment or 'Python trading system')

    def close_position(self, trade: TradeRecord) -> TradeResult:
        """Perform the defined operation."""
        opposite_direction = TRADE_DIRECTION_SELL if trade.type == TRADE_DIRECTION_BUY else TRADE_DIRECTION_BUY
        logger.info(f'Closing order — Symbol: {trade.symbol}, Lot Size: {trade.lot_size}, Direction: {opposite_direction}, Position: {trade.ticket}, Comment: {trade.comment}')
        result = self._open_position(symbol=trade.symbol, size=trade.lot_size, direction=opposite_direction, comment=trade.comment or 'Close position', position=trade.ticket)
        if result.accepted:
            trade.exit_time = PlatformTime.now().strftime(DATETIME_FORMAT)
            trade.status = TRADE_STATUS_CLOSED
            executed_exit_price = getattr(result, 'price', None)
            requested_exit_price = result.request.get('price', None)
            trade.exit_price = executed_exit_price or requested_exit_price
            if result.slippage_exit is not None:
                trade.slippage_exit = result.slippage_exit
        return TradeResult(symbol=result.symbol, lot_size=result.lot_size, accepted=result.accepted, ticket=result.order_id, deal=result.deal, retcode=result.retcode, comment=result.comment, request=result.request)

    def _modify_position(self, ticket: str, sl: Optional[float]=None, tp: Optional[float]=None, comment: str='', symbol: Optional[str]=None, **kwargs) -> TradeResult:
        """Broker-specific trade modification."""
        raise NotImplementedError

    def modify_position(self, trade: TradeRecord) -> bool:
        """Modify an open trade; return True if state changed."""
        return False

    def _open_position(self, symbol: str, size: float, direction: str, sl: float=None, tp: float=None, price: float=None, comment: str='Python trading system', position: str=None, **kwargs) -> OrderResult:
        """Perform the defined operation."""
        symbol_info_tick = mt5.symbol_info_tick(symbol)
        if not symbol_info_tick:
            logger.error(f'Failed to retrieve tick info for symbol: {symbol}')
            return OrderResult(symbol, 0, False, 0, -1, 'Tick error', 0, {})
        price = symbol_info_tick.ask if direction == TRADE_DIRECTION_BUY else symbol_info_tick.bid
        order_type_code = mt5.ORDER_TYPE_BUY if direction == TRADE_DIRECTION_BUY else mt5.ORDER_TYPE_SELL
        request = {'action': mt5.TRADE_ACTION_DEAL, 'symbol': symbol, 'volume': size, 'type': order_type_code, 'price': price, 'deviation': 10, 'magic': 0, 'comment': comment, 'type_time': mt5.ORDER_TIME_GTC, 'type_filling': mt5.ORDER_FILLING_IOC}
        if sl is not None:
            request['sl'] = sl
        if tp is not None:
            request['tp'] = tp
        if position is not None:
            request['position'] = position
        result = mt5.order_send(request)
        if result is None:
            logger.error(f'MT5 order_send returned None for symbol {symbol}')
            return OrderResult(symbol=symbol, lot_size=0, accepted=False, order_id=0, retcode=-1, comment='order_send returned None', deal=0, request=request)
        accepted = result.retcode == mt5.TRADE_RETCODE_DONE
        executed_price = getattr(result, 'price', None) or 0.0
        requested_price = request.get('price', None)
        if executed_price == 0.0:
            executed_price = symbol_info_tick.bid if direction == TRADE_DIRECTION_SELL else symbol_info_tick.ask
        slippage_entry = None
        slippage_exit = None
        if executed_price and requested_price:
            symbol_info = mt5.symbol_info(symbol)
            if symbol_info and symbol_info.trade_tick_size > 0:
                tick_size = symbol_info.trade_tick_size
                tick_value = symbol_info.trade_tick_value or 0.0
                diff_points = abs(executed_price - requested_price) / tick_size
                slippage_value = diff_points * tick_value * size
                if 'position' in request:
                    slippage_exit = round(slippage_value, 2)
                else:
                    slippage_entry = round(slippage_value, 2)
        if accepted:
            logger.info(f'Order placed successfully: order_id={result.order}, deal_id={result.deal}')
        else:
            logger.error(f'Order failed. Retcode: {result.retcode} — {result.comment}')
        return OrderResult(symbol=symbol, lot_size=size, accepted=accepted, order_id=result.order, retcode=result.retcode, comment=result.comment, deal=result.deal, request=request, price=executed_price, slippage_entry=slippage_entry, slippage_exit=slippage_exit)