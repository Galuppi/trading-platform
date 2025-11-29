from typing import Any

from dataclasses import dataclass
from typing import List

@dataclass
class AssetConfig:
    symbol: str
    timeframe: str
    date_from: str
    date_to: str

@dataclass
class DownloaderConfig:
    name: str
    enabled: bool
    assets: List[AssetConfig]