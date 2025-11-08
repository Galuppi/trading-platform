'''"""This module defines classes related to Mt5Connector."""'''
import MetaTrader5 as mt5
import logging
from history.base.base_connector import Connector
from history.common.models.model_connector import ConnectorConfig
logger = logging.getLogger(__name__)

class Mt5Connector(Connector):

    def __init__(self: Any, config: ConnectorConfig) -> Any:
        if config.login is None or config.password is None:
            raise ValueError("MT5 requires 'login' and 'password' in ConnectorConfig.")
        self.login = config.login
        self.password = config.password
        self.server = config.server

    def connect(self: Any) -> bool:
        if not mt5.initialize():
            logger.error(f'MT5 initialize() failed: {mt5.last_error()}')
            return False
        return True
