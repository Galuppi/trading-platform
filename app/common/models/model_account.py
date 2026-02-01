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
    begin_balance: float
    begin_balance_week: float
    profit_floating: float
    profit_total_week: float
    target_reached: bool = False
    break_even_reached: bool = False
    weekly_profit_reached: bool = False

@dataclass
class AccountRisk:
    account_risk_enabled: bool
    account_stop_loss: float
    account_take_profit: float
    account_break_even: float
    account_profit_level: float
    account_take_profit_week: float
