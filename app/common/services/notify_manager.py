from __future__ import annotations
import logging
import urllib.request
from typing import Optional
from app.common.services.platform_time import PlatformTime

logger = logging.getLogger(__name__)

class NotifyManager:
    """Simple ntfy.sh notification sender"""

    def __init__(self, ntfy_topic: str, server_url: str = "https://ntfy.sh", is_backtest: bool = False  ) -> None:
        self.ntfy_topic = ntfy_topic.strip()
        self.server_url = server_url.rstrip("/")
        self.base_url = f"{self.server_url}/{self.ntfy_topic}"
        self.last_message_timestamp = 0
        self.cooldown_minutes = 10
        self.last_message_text = ""
        self.is_backtest = is_backtest

    def _send(self, message: str, title: Optional[str] = None) -> bool:
        if not self.ntfy_topic:
            logger.warning("No ntfy topic configured - notification skipped")
            return False

        headers = {
            "User-Agent": "TradingApp/1.0",
            "Content-Type": "text/plain",
        }

        if title:
            headers["Title"] = title

        data = message.encode("utf-8")

        request = urllib.request.Request(
            self.base_url,
            data=data,
            headers=headers,
            method="POST"
        )

        try:
            with urllib.request.urlopen(request, timeout=8) as response:
                if response.status in (200, 201):
                    return True
                logger.warning("ntfy returned status %d", response.status)
                return False
        except urllib.error.HTTPError as e:
            logger.error("ntfy HTTP error %d: %s", e.code, e.reason)
            return False
        except Exception as e:
            logger.error("Failed to send ntfy notification: %s", str(e))
            return False

    def send_notification(self, message: str, title: str = "Notification") -> bool:
        if self.is_backtest:
            return False
        
        notification_sent_timestamp = PlatformTime.now().timestamp()
        if notification_sent_timestamp - self.last_message_timestamp < 60 * self.cooldown_minutes and message == self.last_message_text:
            return False
        
        self.last_message_timestamp = notification_sent_timestamp
        self.last_message_text = message
        return self._send(message, title=title)
