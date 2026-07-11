from asyncio import sleep
import logging
from history.base.base_downloader import Download
from history.base.base_connector import Connector 
from datetime import datetime
logger = logging.getLogger(__name__)


class Engine:
    def __init__(self, downloaders: list[Download], connector: Connector):
        self.downloaders = downloaders
        self.connector = connector

    def initialize(self) -> None:
        logger.info("Initializing downloaders...")
        for downloader in self.downloaders:
            try:
                downloader.initialize()
            except Exception as e:
                logger.exception(f"Failed to initialize {downloader.config.name}: {e}")
        logger.info("All downloaders initialized.")

    def run(self) -> None:
        self.initialize()
        logger.info("Starting download engine...")

        for downloader in self.downloaders:
            try:
                if not self.connector.connection_check():
                    logger.warning("Connection lost. Attempting to reconnect...")
                    if self.connector.connect():
                        logger.info("Reconnected successfully.")
                    else:
                        logger.error("Reconnection failed. Retrying in 30 seconds...")
                        datetime.sleep(30)
                        continue

                logger.info(f"Running downloader: {downloader.config.name}")
                downloader.run()
                logger.info(f"Finished downloader: {downloader.config.name}")
            except Exception as e:
                logger.exception(f"Downloader '{downloader.config.name}' failed: {e}")

        logger.info("All downloads complete.")
