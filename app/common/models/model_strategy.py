"""Data models representing strategy configuration, market hours, assets, and signals."""

from dataclasses import dataclass
from typing import List, Optional, Dict, Literal

from app.common.config.constants import POSITIONING_CAPITAL


@dataclass
class MarketSession:
    """Open/close time window for a single trading session."""
    open_time: str  # Format: "HH:MM"
    close_time: str  # Format: "HH:MM"


@dataclass
class MarketHours:
    """Market session hours keyed by day of week."""
    sessions: Dict[str, MarketSession]


@dataclass
class AssetConfig:
    """Per-symbol configuration for a strategy (limits, risk, range settings)."""
    symbol: str
    open_min: int
    close_min: int
    max_buy_trades: Optional[int] = 1
    max_sell_trades: Optional[int] = 1
    max_total_trades: Optional[int] = None
    percent_of_capital: float = 100
    risk_percent: Optional[float] = None
    open_day: Optional[int] = None
    close_day: Optional[int] = None
    range_open_min: Optional[int] = None
    range_close_min: Optional[int] = None
    range_stop_loss: Optional[bool] = None
    signal_buy: Optional[bool] = None
    signal_sell: Optional[bool] = None
    signal_symbol: Optional[str] = None
    trade_cooldown_minutes: Optional[int] = None
    reward_risk_ratio: Optional[float] = None
    range_size_restricted: Optional[bool] = None


@dataclass
class StrategyConfig:
    """Full configuration for a strategy, loaded from its config.yaml."""
    name: str
    display_name: str
    total_strategy_capital: float
    percent_of_capital: float
    holiday_calendar: str
    market_hours: MarketHours
    assets: List[AssetConfig]
    positioning: str = POSITIONING_CAPITAL
    enabled: bool = True
    signal_feed: Optional[str] = None
    symbol_mapping_file: Optional[str] = None
    vix_pause_enabled: bool = False
    vix_threshold: Optional[float] = None

    @classmethod
    def from_dict(cls, data: dict) -> "StrategyConfig":
        sessions_raw = data["market_hours"]["sessions"]
        sessions = {
            day: MarketSession(**session)
            for day, session in sessions_raw.items()
        }

        market_hours = MarketHours(
            sessions=sessions
        )

        assets = [AssetConfig(**asset) for asset in data["assets"]]

        return cls(
            name=data["name"],
            total_strategy_capital=data["total_strategy_capital"],
            percent_of_capital=data.get("percent_of_capital", 100),
            positioning=data.get("positioning", "capital"),
            holiday_calendar=data["holiday_calendar"],
            market_hours=market_hours,
            assets=assets
        )

@dataclass
class Signal:
    """A computed entry/exit signal for a symbol."""
    symbol: str
    category: Optional[str]
    sma24: Optional[float]
    sma4: Optional[float]
    sma1: Optional[float]
    countsma24: Optional[int]
    countsma4: Optional[int]
    countsma1: Optional[int]
    timestamp: Optional[str] = None
