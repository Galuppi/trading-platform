from dataclasses import dataclass
from typing import Optional


@dataclass
class NotifyConfig:
    notify_service: str
    notify_server_url: str
    notify_topic: str
    notify_app_token: Optional[str] = None
    notify_user_key: Optional[str] = None   

