import os
from app.common.models.model_notify import NotifyConfig


def load_notify_config() -> NotifyConfig:
    return NotifyConfig(
        notify_service=os.getenv("NOTIFY_SERVICE", "ntfy"),
        notify_server_url=os.getenv("NOTIFY_SERVER_URL", "https://ntfy.sh"),
        notify_topic=os.getenv("NOTIFY_TOPIC", "edgellence"),
        notify_app_token=os.getenv("NOTIFY_APP_TOKEN"),
        notify_user_key=os.getenv("NOTIFY_USER_KEY"),
    )
