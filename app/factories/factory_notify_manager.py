from __future__ import annotations
import logging
from app.common.services.notify_manager import NotifyManager
from app.common.models.model_notify import NotifyConfig
from app.common.services.pushover_manager import PushoverManager


logger = logging.getLogger(__name__)


def get_notify_manager(notify_config: NotifyConfig, is_backtest: bool) -> NotifyManager:
    try:
        notify_service = notify_config.notify_service
        notify_topic = notify_config.notify_topic
        server_url = notify_config.notify_server_url
        app_token = notify_config.notify_app_token
        user_key = notify_config.notify_user_key

    except AttributeError:
        logger.warning("notify_topic and notify_server_url not set")
        notify_topic = "default"
        server_url = "https://ntfy.sh"
    
    if notify_service == "ntfy":
        logger.info("Initializing NotifyManager for topic: %s, server_url: %s", notify_topic, server_url)  
        manager = NotifyManager(notify_topic=notify_topic, server_url=server_url, is_backtest=is_backtest)  
    elif notify_service == "pushover":
        logger.info("Initializing PushoverManager for application: %s, server_url: %s", app_token, server_url) 
        manager = PushoverManager(
            app_token=app_token,
            user_key=user_key,
            server_url=server_url,
            is_backtest=is_backtest
        )
    else:
        logger.warning("Unknown notify service: %s. Defaulting to ntfy.", notify_service)
        manager = NotifyManager(notify_topic=notify_topic, server_url=server_url, is_backtest=is_backtest)
           

    return manager