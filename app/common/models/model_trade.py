"""Data models representing trade inputs, results, records, and orders."""

from dataclasses import dataclass
from typing import Optional

@dataclass
class TradeInput:
    """Input parameters for evaluating a potential trade."""
    symbol: str
    capital: float
    risk_percent: float = 1.0

@dataclass
class TradeResult:
    """Outcome of an evaluated trade."""
    symbol: str
    lot_size: float
    accepted: bool
    ticket: str
    retcode: int
    deal: Optional[str] = None
    close_price: Optional[float] = None
    profit: float = 0.0
    closed: bool = True
    comment: Optional[str] = ""
    request: Optional[dict] = None
    price: Optional[float] = None

@dataclass
class TradeRecord:
    """Persisted record of an opened or closed trade."""
    id: str
    symbol: str
    lot_size: float
    type: str
    ticket: str
    status: str
    timestamp: str
    strategy: str
    entry_price: Optional[float] = None
    exit_price: Optional[float] = None
    exit_time: Optional[str] = None
    stop_loss: Optional[float] = None
    stop_loss_points: Optional[int] = None
    take_profit: Optional[float] = None
    commission: Optional[float] = None
    comment: Optional[str] = None
    magic: Optional[int] = 0
    profit: Optional[float] = None
    slippage_entry: Optional[float] = None
    slippage_exit: Optional[float] = None

@dataclass
class OrderResult:
    """Result of submitting an order to the broker."""
    symbol: str
    lot_size: float
    accepted: bool
    order_id: str
    retcode: int
    comment: str
    deal: Optional[str] = None
    request: Optional[dict] = None
    price: Optional[float] = None
    slippage_entry: Optional[float] = None
    slippage_exit: Optional[float] = None

@dataclass
class OrderRequest:
    """A fully sized order ready to be submitted to the broker."""
    symbol: str
    direction: str
    lot_size: float
    capital: float
    stop_loss: Optional[float] = None
    stop_loss_points: Optional[int] = None
    take_profit: Optional[float] = None
    risk_percent: Optional[float] = None
    reward_risk_ratio: Optional[float] = None
    comment: Optional[str] = ""
    price: Optional[float] = None
    strategy_name: Optional[str] = ""
    magic: Optional[int] = 0

@dataclass
class ProfitResult:
    """Computed profit/loss for a closed trade."""
    profit: float = 0.0
    commission: float = 0.0
    slippage_entry: float = 0.0
    slippage_exit: float = 0.0