from dataclasses import dataclass

@dataclass
class BalanceInfo:
    equity: float
    balance: float
    free_margin: float

@dataclass
class MarginInfo:
    required_margin: float
    has_sufficient: bool

@dataclass
class DailyProfitSnapshot:
    timestamp: str
    equity: float
    balance: float
    profit: float

@dataclass(frozen=True, slots=True)
class StateBalances:
    balance: float
    equity: float
    profit: float