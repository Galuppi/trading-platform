import logging

from history.base.base_connector import Connector
from history.common.models.model_connector import ConnectorConfig

logger = logging.getLogger(__name__)

def get_connector(name: str, config: ConnectorConfig) -> Connector:
    name = name.lower()

    if name == "mt5":
        from history.connectors.mt5.mt5_connector import Mt5Connector
        return Mt5Connector(config)

    if name == "ctrader":
        from history.connectors.ctrader.ctrader_connector import CTraderConnector
        return CTraderConnector(config)

    raise ValueError(f"Unsupported platform: {name}")
