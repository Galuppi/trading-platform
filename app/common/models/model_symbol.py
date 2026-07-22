"""Data models representing symbol metadata, price ranges, and price records."""

from dataclasses import dataclass
from datetime import datetime
from typing import Optional


@dataclass
class SymbolInfo:
    """Metadata describing a tradable symbol."""
    symbol: str
    time: datetime  # UTC timestamp
    ask_price: float
    bid_price: float
    open: float
    high: float
    low: float
    close: float
    lot_size: float


@dataclass
class Range:
    """Tracked high/low price range for a symbol over a session."""
    symbol: str
    high: float
    low: float
    date: datetime  # platform-local timestamp
    range_set: bool = False

@dataclass
class PriceRecord:
    """A single recorded price observation."""
    symbol: str
    time: datetime
    open: float
    high: float
    low: float
    close: float
    volume: float


@dataclass
class SpotPrice:
    """A live bid/ask quote for a symbol, as reported by a broker's spot price feed.

    `bid`/`ask` are None until the first tick containing that side has arrived
    (a broker's spot feed may report bid-only or ask-only ticks), distinct from
    an actual price of zero.
    """
    bid: Optional[float] = None
    ask: Optional[float] = None
    timestamp: int = 0