import logging

from app.base.base_connector import Connector
from app.common.models.model_connector import ConnectorConfig

logger = logging.getLogger(__name__)


class CTraderConnector(Connector):
    def __init__(self, config: ConnectorConfig):
        if not config.api_key or not config.account_id:
            raise ValueError("cTrader requires 'api_key' and 'account_id' in ConnectorConfig.")

        self.api_key = config.api_key
        self.account_id = config.account_id
        self.server = config.server
        self.client_id = config.client_id
        self.client_secret = config.client_secret
        self.refresh_token = config.refresh_token
        self.timezone = config.timezone

    def connect(self) -> bool:
        logger.warning("CTraderConnector.connect() is not implemented.")
        return False
