"""cTrader implementation of the Trade interface."""

import logging
from typing import Any

from app.base.base_trade import Trade
from app.common.config.constants import (
    TRADE_DIRECTION_BUY,
    TRADE_STATUS_CLOSED,
    DATETIME_FORMAT,
)
from app.common.models.model_trade import OrderRequest, ProfitResult, TradeRecord, OrderResult, TradeResult
from app.common.services.platform_time import PlatformTime
from app.common.services.calculator import Calculator
from app.connectors.ctrader.ctrader_session import CTraderSession, EXECUTION_TYPE_FILLED

logger = logging.getLogger(__name__)

# ProtoOATradeSide enum values.
TRADE_SIDE_BUY = 1
TRADE_SIDE_SELL = 2


class CTraderTrade(Trade):
    """cTrader implementation of the Trade interface."""

    def __init__(self, calculator: Calculator):
        self.session = CTraderSession.instance()
        self.calculator = calculator
        if self.calculator is None:
            print("[ERROR] Calculator is None in CTraderTrade constructor!")

    def _lots_to_api_volume(self, symbol: str, lots: float) -> int:
        return self.session.lots_to_api_volume(symbol, lots)

    def open_position(self, order: OrderRequest) -> OrderResult:
        logger.debug(
            f"Placing order — Symbol: {order.symbol}, "
            f"Lot Size: {order.lot_size}, Direction: {order.direction}, "
            f"SL: {order.stop_loss}, TP: {order.take_profit}, Comment: {order.comment}"
        )

        trade_side = TRADE_SIDE_BUY if order.direction == TRADE_DIRECTION_BUY else TRADE_SIDE_SELL
        api_volume = self._lots_to_api_volume(order.symbol, order.lot_size)

        try:
            event = self.session.new_market_order(
                symbol=order.symbol,
                api_volume=api_volume,
                trade_side_enum=trade_side,
                comment=order.comment or "Python trading system",
                label=str(order.strategy_id) if order.strategy_id else "",
            )
        except Exception as error:
            logger.error(f"cTrader open_position failed for {order.symbol}: {error}")
            return OrderResult(
                symbol=order.symbol,
                lot_size=0,
                accepted=False,
                order_id=0,
                retcode=-1,
                comment=str(error),
                deal=0,
                request={"symbol": order.symbol, "volume": api_volume, "tradeSide": trade_side},
            )

        accepted = event.executionType == EXECUTION_TYPE_FILLED and not event.errorCode
        deal = event.deal if event.HasField("deal") else None
        position = event.position if event.HasField("position") else None

        executed_price = deal.executionPrice if deal else (position.price if position else None)
        order_id = event.order.orderId if event.HasField("order") else 0
        position_id = position.positionId if position else 0

        if accepted:
            logger.info(f"Order placed successfully: Symbol={order.symbol}, Position ID={position_id}")
        else:
            logger.error(f"Order failed for {order.symbol}. errorCode={event.errorCode}")

        # SL/TP aren't set on ProtoOANewOrderReq for guaranteed fills in all
        # broker configs the same way MT5 handles it inline; if a stop_loss
        # or take_profit was requested, apply it as a follow-up amend so a
        # rejected amend doesn't block the entry itself.
        if accepted and position_id and (order.stop_loss or order.take_profit):
            self._amend_position_sl_tp(position_id, order.stop_loss, order.take_profit)

        return OrderResult(
            symbol=order.symbol,
            lot_size=order.lot_size,
            accepted=accepted,
            order_id=str(position_id),
            retcode=0 if accepted else -1,
            comment=event.errorCode or "",
            deal=str(deal.dealId) if deal else str(position_id),
            request={"symbol": order.symbol, "volume": api_volume, "tradeSide": trade_side},
            price=executed_price,
            slippage_entry=None,
            slippage_exit=None,
        )

    def close_position(self, trade: TradeRecord) -> TradeResult:
        logger.debug(
            f"Closing order — Symbol: {trade.symbol}, "
            f"Lot Size: {trade.lot_size}, Position: {trade.ticket}, Comment: {trade.comment}"
        )

        position_id = int(trade.ticket)
        api_volume = self._lots_to_api_volume(trade.symbol, trade.lot_size)

        try:
            event = self.session.close_position(position_id, api_volume)
        except Exception as error:
            logger.error(f"cTrader close_position failed for {trade.symbol} (#{position_id}): {error}")
            return TradeResult(
                symbol=trade.symbol,
                lot_size=trade.lot_size,
                accepted=False,
                ticket=trade.ticket,
                retcode=-1,
                comment=str(error),
                request={},
            )

        accepted = event.executionType == EXECUTION_TYPE_FILLED and not event.errorCode
        deal = event.deal if event.HasField("deal") else None

        if accepted:
            trade.exit_time = PlatformTime.now().strftime(DATETIME_FORMAT)
            trade.status = TRADE_STATUS_CLOSED
            trade.exit_price = deal.executionPrice if deal else None
            trade.slippage_exit = None
            logger.info(f"Position closed successfully: Symbol={trade.symbol}, Position ID={position_id}")
        else:
            logger.error(f"Close failed for {trade.symbol} (#{position_id}). errorCode={event.errorCode}")

        return TradeResult(
            symbol=trade.symbol,
            lot_size=trade.lot_size,
            accepted=accepted,
            ticket=trade.ticket,
            deal=str(deal.dealId) if deal else None,
            retcode=0 if accepted else -1,
            comment=event.errorCode or "",
            request={"positionId": position_id, "volume": api_volume},
        )

    def _calculate_unrealized_profit(self, trade: TradeRecord) -> ProfitResult:
        return self.calculator.calculate_profit(trade, False)

    def modify_position(self, trade: TradeRecord) -> bool:
        """Modify an open trade; return True if state changed."""
        result = self._calculate_unrealized_profit(trade)
        if abs(result.profit) > 1.0:
            trade.profit = result.profit
            trade.commission = result.commission
            trade.slippage_entry = result.slippage_entry
            return True
        else:
            return False

    def _amend_position_sl_tp(self, position_id: int, stop_loss: float, take_profit: float) -> None:
        try:
            self.session.amend_position_sl_tp(position_id, stop_loss, take_profit)
        except Exception as error:
            logger.warning(f"Failed to amend SL/TP on position {position_id}: {error}")
