"""Discovers, configures, and instantiates all enabled strategies."""

import importlib
import yaml
import logging
from pathlib import Path
from typing import List, Iterator, Optional, Tuple, Type

from app.base.base_strategy import Strategy
from app.base.base_connector import Connector
from app.base.base_account import Account
from app.base.base_symbol import Symbol
from app.base.base_trade import Trade
from app.common.services.calculator import Calculator
from app.common.services.state_manager import StateManager
from app.common.services.news_manager import NewsManager
from app.common.services.risk_manager import RiskManager
from app.common.services.vix_manager import VixManager
from app.common.services.pushover_manager import PushoverManager
from app.common.config.paths import STRATEGY_PATH
from app.common.models.model_strategy import (
    StrategyConfig,
    AssetConfig,
    MarketHours,
    MarketSession
)
from app.common.config.loaders.loader_holiday import load_holiday_calendar
from app.common.config.loaders.loader_strategy_profile import load_strategy_config_profile

logger = logging.getLogger(__name__)


def get_strategy_config(config_path: Path) -> StrategyConfig:
    with open(config_path, "r", encoding="utf-8") as f:
        raw_config = yaml.safe_load(f)

    assets = [AssetConfig(**a) for a in raw_config.get("assets", [])]

    raw_hours = raw_config.get("market_hours", {})
    raw_sessions = raw_hours.get("sessions", {})

    sessions = {
        day: MarketSession(
            open_time=times["open_time"],
            close_time=times["close_time"]
        )
        for day, times in raw_sessions.items()
    }

    market_hours = MarketHours(
        sessions=sessions
    )

    return StrategyConfig(
        name=raw_config.get("name", ""),
        display_name=raw_config.get("display_name", ""),
        total_strategy_capital=raw_config.get("total_strategy_capital", 10000),
        percent_of_capital=raw_config.get("percent_of_capital", 100),
        positioning=raw_config.get("positioning", "capital"),
        holiday_calendar=raw_config.get("holiday_calendar", "us"),
        market_hours=market_hours,
        assets=assets,
        enabled=raw_config.get("enabled", True),
        strategy_id=raw_config.get("strategy_id", 0),
        signal_feed=raw_config.get("signal_feed", ""),
        vix_pause_enabled=raw_config.get("vix_pause_enabled", False),
        vix_threshold=raw_config.get("vix_threshold"),
    )


def resolve_strategy_config_path(item: Path, profile: str) -> Optional[Path]:
    """Resolve the config file for a strategy folder given the active profile.

    Prefers '{profile}_config.yaml' when a profile is set and the file exists,
    falling back to the default 'config.yaml'. Returns None if neither exists.
    """
    if profile:
        profile_config_file = item / f"{profile}_config.yaml"
        if profile_config_file.exists():
            return profile_config_file

    default_config_file = item / "config.yaml"
    return default_config_file if default_config_file.exists() else None


def discover_strategies() -> Iterator[Tuple[Path, Path, Path]]:
    profile = load_strategy_config_profile()

    for item in STRATEGY_PATH.iterdir():
        if item.is_dir() and not item.name.startswith("__"):
            strategy_file = item / "strategy.py"
            config_file = resolve_strategy_config_path(item, profile)

            if strategy_file.exists() and config_file is not None:
                logger.info(f"Strategy '{item.name}': using config '{config_file.name}'")
                yield item, strategy_file, config_file
            else:
                logger.warning(
                    f"Skipping '{item.name}': strategy.py or a config file not found"
                )


def get_strategy_class(module_path: str, class_name: str) -> Type[Strategy]:
    module = importlib.import_module(module_path)
    if not hasattr(module, class_name):
        raise ImportError(f"Class '{class_name}' not found in '{module_path}'")
    return getattr(module, class_name)


def get_strategies(
    connector: Connector,
    account: Account,
    symbol: Symbol,
    trader: Trade,
    calculator: Calculator,
    state_manager: StateManager,
    news_manager: NewsManager,
    risk_manager: RiskManager,
    vix_manager: VixManager,
    notify_manager: PushoverManager,
) -> List[Strategy]:
    strategies = []

    for item, _, config_file in discover_strategies():
        try:
            config = get_strategy_config(config_file)

            if not config.enabled:
                logger.info(f"Strategy '{config.name}' is disabled in config.")
                continue

            module_path = f"app.strategies.{item.name}.strategy"
            class_name = (
                "".join(part.capitalize() for part in item.name.split("_")) + "Strategy"
            )

            strategy_class = get_strategy_class(module_path, class_name)

            strategy = strategy_class(config=config)
            strategy.attach_services(
                connector=connector,
                account=account,
                symbol=symbol,
                trader=trader,
                calculator=calculator,
                state_manager=state_manager,
                news_manager=news_manager,
                risk_manager=risk_manager,
                vix_manager=vix_manager,
                notify_manager=notify_manager,
            )
            
            holidays = load_holiday_calendar(config.holiday_calendar)
            strategy.set_holidays(holidays)

            strategies.append(strategy)

        except Exception as e:
            logger.exception(f"Failed to load strategy from '{item.name}': {e}")

    return strategies
