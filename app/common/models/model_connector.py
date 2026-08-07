"""Configuration model for a platform connector (MT5 or cTrader)."""

from dataclasses import dataclass
from typing import Optional


@dataclass
class ConnectorConfig:
    """Configuration for connecting to a trading platform (MT5 or cTrader)."""
    type: str
    environment: str
    server: str
    timezone: str
    offset: int
    login: Optional[int]
    password: Optional[str]
    terminal_path: Optional[str]
    api_key: Optional[str]
    account_id: Optional[str]
    client_id: Optional[str]
    client_secret: Optional[str]
    refresh_token: Optional[str]
