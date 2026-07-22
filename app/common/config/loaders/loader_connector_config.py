"""Loads platform connector configuration (credentials, server, environment) from environment variables."""

import os
from app.common.models.model_connector import ConnectorConfig
from app.common.config.constants import ENVIRONMENT_DEVELOPMENT


def str_to_bool(value: str) -> bool:
    return value.lower() in ("1", "true", "yes", "on")


def load_connector_config() -> ConnectorConfig:
    platform_type = (os.getenv("PLATFORM_TYPE", "") or "").lower()
    environment = (os.getenv("PLATFORM_ENVIRONMENT", ENVIRONMENT_DEVELOPMENT) or ENVIRONMENT_DEVELOPMENT).lower()

    return ConnectorConfig(
        type=platform_type,
        environment=environment,
        server=os.getenv("PLATFORM_SERVER", ""),
        timezone=os.getenv("PLATFORM_TIMEZONE", ""),
        offset=int(os.getenv("PLATFORM_TIME_OFFSET", "0")),
        login=int(os.getenv("MT5_LOGIN", "0")),
        password=os.getenv("MT5_PASSWORD"),
        terminal_path=os.getenv("MT5_TERMINAL_PATH"),
        api_key=os.getenv("CTRADER_API_KEY"),
        account_id=os.getenv("CTRADER_ACCOUNT_ID"),
        client_id=os.getenv("CTRADER_CLIENT_ID"),
        client_secret=os.getenv("CTRADER_CLIENT_SECRET"),
        refresh_token=os.getenv("CTRADER_REFRESH_TOKEN"),
    )
