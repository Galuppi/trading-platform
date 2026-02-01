from __future__ import annotations
import logging
from app.common.config.constants import NOTIFY_DEFAULT_TOPIC, MODE_BACKTEST
from app.common.services.notify_manager import NotifyManager


logger = logging.getLogger(__name__)


def get_notify_manager(ntfy_topic: str = NOTIFY_DEFAULT_TOPIC, connector_config=None) -> NotifyManager:
    is_backtest = connector_config.mode == MODE_BACKTEST
    logger.info("Initializing NotifyManager for topic: %s", ntfy_topic)  
    manager = NotifyManager(ntfy_topic=ntfy_topic, is_backtest=is_backtest)       
    return manager