import logging
from app.common.system.news_manager import NewsManager

logger = logging.getLogger(__name__)

def load_news_manager(window_minutes: int = 10) -> NewsManager:
    logger.info("Initializing NewsManager")
    manager = NewsManager(window_minutes=window_minutes)
    return manager