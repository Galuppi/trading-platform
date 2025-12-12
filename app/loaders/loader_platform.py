import logging

from app.base.base_account import Account
from app.base.base_symbol import Symbol
from app.base.base_connector import Connector
from app.base.base_trade import Trade
from app.base.base_calculator import Calculator
from app.common.models.model_connector import ConnectorConfig
from app.common.system.backtest_summary import BacktestSummary
from app.common.models.model_backtest import BacktestConfig 


logger = logging.getLogger(__name__)

def get_connector(name: str, config: ConnectorConfig) -> Connector:
    name = name.lower()

    if name == "mt5":
        from app.connectors.mt5.mt5_connector import Mt5Connector
        return Mt5Connector(config)

    if name == "ctrader":
        from app.connectors.ctrader.ctrader_connector import CTraderConnector
        return CTraderConnector(config)

    if name == "mt5tester":
        from app.connectors.mt5tester.mt5tester_connector import Mt5testerConnector
        return Mt5testerConnector(config)

    raise ValueError(f"Unsupported platform: {name}")


def get_trade(name: str, symbol: Symbol=None, calculator: Calculator = None, summary_writer: BacktestSummary = None) -> Trade:
    name = name.lower()

    if name == "mt5":
        from app.connectors.mt5.mt5_trade import Mt5Trade
        return Mt5Trade()

    if name == "ctrader":
        from app.connectors.ctrader.ctrader_trade import CTraderTrade
        return CTraderTrade()

    if name == "mt5tester":
        from app.connectors.mt5tester.mt5tester_trade import Mt5testerTrade
        return Mt5testerTrade(symbol, calculator, summary_writer)

    raise ValueError(f"Unsupported trade system for platform: {name}")


def get_symbol(name: str, backtester_config=None, account=None) -> Symbol:
    name = name.lower()

    if name == "mt5":
        from app.connectors.mt5.mt5_symbol import Mt5Symbol
        return Mt5Symbol()

    if name == "ctrader":
        from app.connectors.ctrader.ctrader_symbol import CTraderSymbol
        return CTraderSymbol()

    if name == "mt5tester":
        from app.connectors.mt5tester.mt5tester_symbol import Mt5testerSymbol
        return Mt5testerSymbol(backtester_config, account)

    raise ValueError(f"Unsupported symbol service for platform: {name}")


def get_account(name: str, backtester_config:BacktestConfig=None) -> Account:
    name = name.lower()

    if name == "mt5":
        from app.connectors.mt5.mt5_account import Mt5Account
        return Mt5Account()

    if name == "ctrader":
        from app.connectors.ctrader.ctrader_account import CTraderAccount
        return CTraderAccount()

    if name == "mt5tester":
        from app.connectors.mt5tester.mt5tester_account import Mt5testerAccount
        return Mt5testerAccount(backtester_config)

    raise ValueError(f"Unsupported account service for platform: {name}")


def get_calculator(name: str, symbol: Symbol, account: Account, backtester_config:BacktestConfig=None) -> Calculator:
    name = name.lower()

    if name == "mt5":
        from app.connectors.mt5.mt5_calculator import Mt5Calculator
        return Mt5Calculator(symbol, account)

    if name == "ctrader":
        from app.connectors.ctrader.ctrader_calculator import CTraderCalculator
        return CTraderCalculator(symbol, account)

    if name == "mt5tester":
        from app.connectors.mt5tester.mt5tester_calculator import Mt5testerCalculator
        return Mt5testerCalculator(symbol, account, backtester_config)

    raise ValueError(f"Unsupported calculator for platform: {name}")
