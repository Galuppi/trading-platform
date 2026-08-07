"""Builds platform-specific connector, trade, symbol, and account instances by platform name."""

import logging

from app.base.base_account import Account
from app.base.base_symbol import Symbol
from app.base.base_connector import Connector
from app.base.base_trade import Trade
from app.common.services.calculator import Calculator
from app.common.services.state_manager import StateManager
from app.common.models.model_connector import ConnectorConfig


logger = logging.getLogger(__name__)


def get_connector(name: str, config: ConnectorConfig, state_manager: StateManager = None) -> Connector:
    name = name.lower()

    if name == "mt5":
        from app.connectors.mt5.mt5_connector import Mt5Connector
        return Mt5Connector(config, state_manager)

    if name == "ctrader":
        from app.connectors.ctrader.ctrader_connector import CTraderConnector
        return CTraderConnector(config, state_manager)

    raise ValueError(f"Unsupported platform: {name}")


def get_trade(name: str, symbol: Symbol = None, calculator: Calculator = None) -> Trade:
    name = name.lower()

    if name == "mt5":
        from app.connectors.mt5.mt5_trade import Mt5Trade
        return Mt5Trade(calculator)

    if name == "ctrader":
        from app.connectors.ctrader.ctrader_trade import CTraderTrade
        return CTraderTrade(calculator)

    raise ValueError(f"Unsupported trade system for platform: {name}")


def get_symbol(name: str) -> Symbol:
    name = name.lower()

    if name == "mt5":
        from app.connectors.mt5.mt5_symbol import Mt5Symbol
        return Mt5Symbol()

    if name == "ctrader":
        from app.connectors.ctrader.ctrader_symbol import CTraderSymbol
        return CTraderSymbol()

    raise ValueError(f"Unsupported symbol service for platform: {name}")


def get_account(name: str) -> Account:
    name = name.lower()

    if name == "mt5":
        from app.connectors.mt5.mt5_account import Mt5Account
        return Mt5Account()

    if name == "ctrader":
        from app.connectors.ctrader.ctrader_account import CTraderAccount
        return CTraderAccount()

    raise ValueError(f"Unsupported account service for platform: {name}")
