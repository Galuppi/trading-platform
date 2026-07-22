"""Builds the PushoverManager instance from notify configuration."""

import logging
from app.common.services.pushover_manager import PushoverManager
from app.common.models.model_notify import NotifyConfig

logger = logging.getLogger(__name__)


def get_notify_manager(notify_config: NotifyConfig) -> PushoverManager:
    logger.info(
        "Initializing PushoverManager for application: %s, server_url: %s",
        notify_config.notify_app_token,
        notify_config.notify_server_url,
    )
    return PushoverManager(
        app_token=notify_config.notify_app_token,
        user_key=notify_config.notify_user_key,
        server_url=notify_config.notify_server_url,
    )
