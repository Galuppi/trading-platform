import logging
from app.base.base_trade import Trade
from app.common.models.model_trade import OrderRequest, TradeRecord, OrderResult, TradeResult

logger = logging.getLogger(__name__)


class CtraderTrade(Trade):
    def open_position(self, order: OrderRequest) -> OrderResult:
        logger.warning(f"[STUB] open_position not yet implemented for cTrader — order: {order}")
        return OrderResult(
            
            accepted=False,
            ticket=0,
            deal=0,
            retcode=-1,
            comment="open_position stub not implemented",
            request={}
        )

    def close_position(self, trade: TradeRecord) -> TradeResult:
        logger.warning(f"[STUB] close_position not yet implemented for cTrader — trade: {trade}")
        return TradeResult(
            accepted=False,
            ticket=0,
            deal=0,
            retcode=-1,
            comment="close_position stub not implemented",
            request={}
        )