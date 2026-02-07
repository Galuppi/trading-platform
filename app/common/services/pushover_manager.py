from __future__ import annotations
import logging
from turtle import title
import urllib.request
import urllib.parse
from typing import Optional
from app.common.services.platform_time import PlatformTime

logger = logging.getLogger(__name__)

class PushoverManager:
    def __init__(
        self,
        app_token: str,
        user_key: str,
        server_url: str,
        title: str = "Notification",
        is_backtest: bool = False,
    ) -> None:
        self.app_token = app_token.strip()
        self.user_key = user_key.strip()
        self.server_url = server_url.rstrip("/")
        self.title = title
        self.last_message_timestamp = 0
        self.cooldown_minutes = 10
        self.last_message_text = ""
        self.is_backtest = is_backtest

    def _send(
        self,
        message: str,
        title: str,
        priority: Optional[int] = None,
        sound: Optional[str] = None,
        device: Optional[str] = None,
        url: Optional[str] = None,
        url_title: Optional[str] = None,
        retry: Optional[int] = None,
        expire: Optional[int] = None,
    ) -> bool:
        if not self.app_token or not self.user_key:
            logger.warning("Pushover app_token or user_key missing - notification skipped")
            return False

        post_data = {
            "token": self.app_token,
            "user": self.user_key,
            "message": message,
            "title": title,
        }

        if title:
            post_data["title"] = title
        if priority is not None:
            post_data["priority"] = str(priority)
        if sound:
            post_data["sound"] = sound
        if device:
            post_data["device"] = device
        if url:
            post_data["url"] = url
            if url_title:
                post_data["url_title"] = url_title
        if retry is not None:
            post_data["retry"] = str(retry)
        if expire is not None:
            post_data["expire"] = str(expire)

        data = urllib.parse.urlencode(post_data).encode("utf-8")
        headers = {
            "User-Agent": "TradingApp/1.0",
            "Content-Type": "application/x-www-form-urlencoded",
        }

        request = urllib.request.Request(
            self.server_url,
            data=data,
            headers=headers,
            method="POST"
        )

        try:
            with urllib.request.urlopen(request, timeout=8) as response:
                if response.status == 200:
                    return True
                logger.warning("Pushover returned status %d", response.status)
                return False
        except urllib.error.HTTPError as e:
            logger.error("Pushover HTTP error %d: %s", e.code, e.reason)
            return False
        except Exception as e:
            logger.error("Failed to send Pushover notification: %s", str(e))
            return False

    def send_notification(
        self,
        message: str,
        title: str,
        priority: Optional[int] = None,
        sound: Optional[str] = None,
        device: Optional[str] = None,
        url: Optional[str] = None,
        url_title: Optional[str] = None,
        retry: Optional[int] = None,
        expire: Optional[int] = None,
    ) -> bool:
        if self.is_backtest:
            return False
        
        notification_sent_timestamp = PlatformTime.now().timestamp()
        if (
            notification_sent_timestamp - self.last_message_timestamp < 60 * self.cooldown_minutes
            and message == self.last_message_text
        ):
            return False

        self.last_message_timestamp = notification_sent_timestamp
        self.last_message_text = message

        return self._send(
            message,
            title=title,
            priority=priority,
            sound=sound,
            device=device,
            url=url,
            url_title=url_title,
            retry=retry,
            expire=expire,
        )