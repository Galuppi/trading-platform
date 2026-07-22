"""Loads Pushover notification configuration from environment variables."""

import os
from app.common.models.model_notify import NotifyConfig


def load_notify_config() -> NotifyConfig:
    return NotifyConfig(
        notify_server_url=os.getenv("NOTIFY_SERVER_URL", "https://api.pushover.net/1/messages.json"),
        notify_app_token=os.getenv("NOTIFY_APP_TOKEN"),
        notify_user_key=os.getenv("NOTIFY_USER_KEY"),
    )
