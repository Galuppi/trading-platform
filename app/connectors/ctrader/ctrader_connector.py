"""cTrader implementation of the Connector interface."""

import logging

from app.base.base_connector import Connector
from app.common.models.model_connector import ConnectorConfig
from app.connectors.ctrader.ctrader_session import CTraderSession
from app.common.services.state_manager import StateManager

logger = logging.getLogger(__name__)


class CTraderConnector(Connector):
    """cTrader implementation of the Connector interface, backed by a shared CTraderSession."""

    def __init__(self, config: ConnectorConfig, state_manager: StateManager = None):
        self.config = config
        self.session = CTraderSession.instance()
        self.session.configure(config, state_manager)

    def connect(self) -> bool:
        """Establish the cTrader Open API session (TCP/SSL + OAuth + account auth + symbol cache)."""
        logger.info(
            f"Attempting to connect to cTrader: Account {self.config.account_id}, "
            f"Environment: {self.config.environment}"
        )
        return self.session.connect()

    def connection_check(self) -> bool:
        """Checks if the cTrader connection is still valid; reconnects on failure."""
        if self.session.connection_check():
            return True

        logger.warning("cTrader connection check failed. Attempting to reconnect.")
        return self.session.connect()
