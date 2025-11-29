from typing import Any

from dataclasses import dataclass
from datetime import datetime

@dataclass
class SymbolInfo:
    symbol: str
    time: datetime
    ask_price: float
    bid_price: float
    open: float
    high: float
    low: float
    close: float
    lot_size: float

@dataclass
class Range:
    symbol: str
    high: float
    low: float
    date: datetime
    range_set: bool = False

@dataclass
class PriceRecord:
    symbol: str
    time: datetime
    open: float
    high: float
    low: float
    close: float
    volume: float