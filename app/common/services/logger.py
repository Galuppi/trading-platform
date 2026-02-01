import os
import logging
from app.common.services.platform_time import PlatformTime
from app.common.config.constants import MODE_LIVE
from pathlib import Path

def setup_logger(log_path: Path, mode: str) -> logging.Logger:
    """Initialize and configure the application logger."""
    root_logger = logging.getLogger()

    for handler in root_logger.handlers[:]:
        root_logger.removeHandler(handler)

    date_str = PlatformTime.now().strftime("%Y%m%d")
    if mode != MODE_LIVE:
        date_str = PlatformTime.now().strftime("%Y%m")

    log_file = log_path / f"{mode.lower()}_{date_str}.log"
    log_path.mkdir(parents=True, exist_ok=True)

    level_str = os.getenv("LOG_LEVEL", "INFO").upper()
    log_level = getattr(logging, level_str, logging.INFO)

    logging.basicConfig(
        level=log_level,
        format="%(asctime)s [%(levelname)s] [%(name)s] %(message)s",
        handlers=[
            logging.FileHandler(log_file, encoding="utf-8"),
            logging.StreamHandler(),
        ],
    )

    logger = logging.getLogger(__name__)
    if mode == MODE_LIVE:
        logger.info(f"Logger initialized — File: {log_file}")
        
    return logger
