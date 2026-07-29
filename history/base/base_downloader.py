from abc import ABC, abstractmethod
from history.common.models.model_downloader import DownloaderConfig


class Download(ABC):
    @abstractmethod
    def run(self, config: DownloaderConfig) -> None:
        """Execute the download process using the given configuration."""
        pass
