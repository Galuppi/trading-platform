from typing import Any

import MetaTrader5 as mt5
import logging
from app.base.base_connector import Connector
from app.common.models.model_connector import ConnectorConfig
logger = logging.getLogger(__name__)

class Mt5Connector(Connector):

    def __init__(self, config: ConnectorConfig) -> Any:
        """Perform the defined operation."""
        if config.login is None or config.password is None:
            raise ValueError("MT5 requires 'login' and 'password' in ConnectorConfig.")

    def connect(self) -> bool:
        """Perform the defined operation."""
        if not mt5.initialize():
            logger.error(f'MT5 initialize() failed: {mt5.last_error()}')
            return False
        return True