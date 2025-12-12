import os
from app.common.models.model_connector import ConnectorConfig
from app.common.config.constants import MODE_BACKTEST, MODE_LIVE

def str_to_bool(value: str) -> bool:
    return value.lower() in ("1", "true", "yes", "on")

def load_connector_config() -> ConnectorConfig:
    platform_type=(os.getenv("PLATFORM_TYPE", "") or "").lower()
    platform_mode = MODE_BACKTEST if "test" in platform_type else MODE_LIVE


    return ConnectorConfig(
        type=platform_type,
        mode=platform_mode,
        server=os.getenv("PLATFORM_SERVER", ""),
        timezone=os.getenv("PLATFORM_TIMEZONE", ""),
        offset=int(os.getenv("PLATFORM_TIME_OFFSET", "0")),
        login=int(os.getenv("ACCOUNT_LOGIN", "0")),
        password=os.getenv("ACCOUNT_PASSWORD"),
        api_key=os.getenv("PLATFORM_API_KEY"),
        account_id=os.getenv("PLATFORM_ACCOUNT_ID"),
        client_id=os.getenv("PLATFORM_CLIENT_ID"),
        client_secret=os.getenv("PLATFORM_CLIENT_SECRET"),
        refresh_token=os.getenv("PLATFORM_REFRESH_TOKEN"),
    )
