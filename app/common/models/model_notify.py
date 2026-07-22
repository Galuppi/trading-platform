"""Configuration model for the Pushover notification service."""

from dataclasses import dataclass


@dataclass
class NotifyConfig:
    """Configuration for the Pushover notification service."""
    notify_server_url: str
    notify_app_token: str
    notify_user_key: str
