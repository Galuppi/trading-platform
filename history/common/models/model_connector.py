from dataclasses import dataclass
from typing import Optional

@dataclass
class ConnectorConfig:
    type: str
    mode: str
    server: str
    timezone: str
    login: Optional[int]
    password: Optional[str]
    api_key: Optional[str]
    account_id: Optional[str]
    client_id: Optional[str]
    client_secret: Optional[str]
    refresh_token: Optional[str]
