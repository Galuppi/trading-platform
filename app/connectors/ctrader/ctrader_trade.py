from typing import Any

import logging
from app.base.base_trade import Trade
from app.common.models.model_trade import OrderRequest, TradeRecord, OrderResult, TradeResult
logger = logging.getLogger(__name__)

class CtraderTrade(Trade):

    def open_position(self, order: OrderRequest) -> OrderResult:
        """Perform the defined operation."""
        logger.warning(f'[STUB] open_position not yet implemented for cTrader — order: {order}')
        return OrderResult(accepted=False, ticket=0, deal=0, retcode=-1, comment='open_position stub not implemented', request={})

    def close_position(self, trade: TradeRecord) -> TradeResult:
        """Perform the defined operation."""
        logger.warning(f'[STUB] close_position not yet implemented for cTrader — trade: {trade}')
        return TradeResult(accepted=False, ticket=0, deal=0, retcode=-1, comment='close_position stub not implemented', request={})

    def _open_position(self, symbol: str, size: float, direction: str, order_type: str, sl: float=None, tp: float=None, price: float=None, comment: str='', **kwargs) -> OrderResult:
        """Perform the defined operation."""
        logger.warning(f'[STUB] _open_position not yet implemented for cTrader — symbol: {symbol}, direction: {direction}')
        return OrderResult(accepted=False, order_id=0, deal=0, retcode=-1, comment='_open_position stub not implemented', request={})