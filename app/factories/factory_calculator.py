from app.base.base_account import Account
from app.base.base_symbol import Symbol
from app.common.services.calculator import Calculator
from app.common.models.model_backtest import BacktestConfig 

def get_calculator(symbol: Symbol, account: Account) -> Calculator:
     return Calculator(symbol, account)

 