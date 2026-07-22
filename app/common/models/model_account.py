"""Data models representing account balance, margin, and risk snapshots."""

from dataclasses import dataclass

@dataclass
class BalanceInfo:
    """Snapshot of account balance and profit at a point in time."""
    equity: float
    balance: float
    free_margin: float

@dataclass
class MarginInfo:
    """Snapshot of account margin usage and free margin."""
    required_margin: float
    has_sufficient: bool

@dataclass
class AccountSnapshot:
    """Persisted snapshot of equity, balance, and daily risk-target status."""
    timestamp: str
    equity: float
    balance: float
    begin_balance: float
    begin_balance_week: float
    profit_floating: float
    profit_total_week: float
    target_reached: bool = False
    break_even_reached: bool = False
    weekly_profit_reached: bool = False

@dataclass
class AccountRisk:
    """Configured account-level risk thresholds."""
    account_risk_enabled: bool
    account_stop_loss: float
    account_take_profit: float
    account_break_even: float
    account_profit_level: float
    account_take_profit_week: float
