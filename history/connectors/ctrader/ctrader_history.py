from typing import Any

import logging
from datetime import datetime
from history.base.base_history import History
logger = logging.getLogger(__name__)

class CTraderHistory(History):

    def get_historical_data(self, symbol: str, timeframe: str, start_date: datetime, end_date: datetime) -> Any:
        """Perform the defined operation."""
        logger.warning(f"[CTraderHistory] Data request for symbol='{symbol}', timeframe='{timeframe}' from {start_date} to {end_date} — Not yet implemented.")
        raise NotImplementedError('CTraderHistory is not implemented yet.')