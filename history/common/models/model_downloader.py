from dataclasses import dataclass
from typing import List

@dataclass
class AssetConfig:
    symbol: str
    timeframe: str
    date_from: str  # Format: DD-MM-YYYY
    date_to: str    # Format: DD-MM-YYYY

@dataclass
class DownloaderConfig:
    name: str
    enabled: bool
    assets: List[AssetConfig]


