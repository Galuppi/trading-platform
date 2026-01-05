import logging

from dotenv import load_dotenv
load_dotenv()

from history.common.config.paths import LOG_PATH
from history.common.system.logger import setup_logger
from history.loaders.loader_connector_config import load_connector_config
from history.loaders.loader_platform import get_connector
from history.loaders.loader_downloader import downloader_registry
from history.loaders.loader_history import get_history
from history.runtime.engine import Engine
from history.common.config.constants import MODE_HISTORY


logger = logging.getLogger(__name__)

if __name__ == "__main__":
    setup_logger(LOG_PATH, MODE_HISTORY)
    logger.info("Starting downloader runtime...")

    try:
        connector_config = load_connector_config()
        platform_name = connector_config.type.lower()

        connector = get_connector(platform_name, connector_config)

        if not connector.connect():
            logger.error("Failed to connect to trading platform.")
            raise RuntimeError("Platform connection failed.")

        history = get_history(platform_name)
        downloaders = downloader_registry(connector, history)

        engine = Engine(downloaders=downloaders)
        engine.run()

    except Exception as e:
        logger.exception(f"Fatal error: {e}")
        input("Press Enter to exit...")
