from app.common.models.model_trade import TradeRecord
from app.common.system.platform_time import PlatformTime
from app.common.config.constants import TRADE_STATUS_OPEN


def create_trade_record(
    result,
    order,
    entry_price: float,
    strategy_name: str
) -> TradeRecord:
    return TradeRecord(
        id=result.order_id,
        symbol=order.symbol,
        lot_size=order.lot_size,
        type=order.direction,
        ticket=result.order_id,
        status=TRADE_STATUS_OPEN,
        timestamp=PlatformTime.datetime_str(),
        strategy=strategy_name,
        comment=order.comment,
        entry_price=entry_price,
        stop_loss=order.stop_loss,
        take_profit=order.take_profit,
        stop_loss_points=order.stop_loss_points,
        profit=0.0,
        slippage_entry=result.slippage_entry,
        slippage_exit=result.slippage_exit,
    )
