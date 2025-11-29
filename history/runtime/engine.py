from typing import Any

import logging
from history.base.base_downloader import Download
logger = logging.getLogger(__name__)

class Engine:

    def __init__(self, downloaders: list[Download]) -> Any:
        """Perform the defined operation."""
        self.downloaders = downloaders

    def initialize(self) -> None:
        """Perform the defined operation."""
        logger.info('Initializing downloaders...')
        for downloader in self.downloaders:
            try:
                downloader.initialize()
            except Exception as e:
                logger.exception(f'Failed to initialize {downloader.config.name}: {e}')
        logger.info('All downloaders initialized.')

    def run(self) -> None:
        """Perform the defined operation."""
        self.initialize()
        logger.info('Starting download engine...')
        for downloader in self.downloaders:
            try:
                logger.info(f'Running downloader: {downloader.config.name}')
                downloader.run()
                logger.info(f'Finished downloader: {downloader.config.name}')
            except Exception as e:
                logger.exception(f"Downloader '{downloader.config.name}' failed: {e}")
        logger.info('All downloads complete.')