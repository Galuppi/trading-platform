from typing import Any

import importlib
import yaml
import logging
from pathlib import Path
from app.common.config.paths import STRATEGY_PATH
from app.common.models.model_strategy import StrategyConfig, AssetConfig, MarketHours, MarketSession
from app.loaders.loader_holiday import load_holiday_calendar
logger = logging.getLogger(__name__)

def strategy_registry_config(config_path: Path) -> StrategyConfig:
    """Perform the defined operation."""
    with open(config_path, 'r', encoding='utf-8') as f:
        raw_config = yaml.safe_load(f)
    assets = [AssetConfig(**a) for a in raw_config.get('assets', [])]
    raw_hours = raw_config.get('market_hours', {})
    raw_sessions = raw_hours.get('sessions', {})
    sessions = {day: MarketSession(open_time=times['open_time'], close_time=times['close_time']) for day, times in raw_sessions.items()}
    market_hours = MarketHours(sessions=sessions)
    return StrategyConfig(name=raw_config.get('name', ''), display_name=raw_config.get('display_name', ''), total_strategy_capital=raw_config.get('total_strategy_capital', 10000), percent_of_capital=raw_config.get('percent_of_capital', 100), positioning=raw_config.get('positioning', 'capital'), holiday_calendar=raw_config.get('holiday_calendar', 'us'), market_hours=market_hours, assets=assets, enabled=raw_config.get('enabled', True), signal_feed=raw_config.get('signal_feed', ''))

def discover_strategies() -> Any:
    """Perform the defined operation."""
    for item in STRATEGY_PATH.iterdir():
        if item.is_dir() and (not item.name.startswith('__')):
            strategy_file = item / 'strategy.py'
            config_file = item / 'config.yaml'
            if strategy_file.exists() and config_file.exists():
                yield (item, strategy_file, config_file)
            else:
                logger.warning(f"Skipping '{item.name}': strategy.py or config.yaml not found")

def strategy_registry_class(module_path: str, class_name: str) -> Any:
    """Perform the defined operation."""
    module = importlib.import_module(module_path)
    if not hasattr(module, class_name):
        raise ImportError(f"Class '{class_name}' not found in '{module_path}'")
    return getattr(module, class_name)

def strategy_registry(connector: Any, account: Any, symbol: Any, trader: Any, calculator: Any, state_manager: Any) -> list:
    """Perform the defined operation."""
    strategies = []
    for item, _, config_file in discover_strategies():
        try:
            config = strategy_registry_config(config_file)
            if not config.enabled:
                logger.info(f"Strategy '{config.name}' is disabled in config.")
                continue
            module_path = f'app.strategies.{item.name}.strategy'
            class_name = ''.join((part.capitalize() for part in item.name.split('_'))) + 'Strategy'
            strategy_class = strategy_registry_class(module_path, class_name)
            strategy = strategy_class(config=config)
            strategy.attach_services(connector=connector, account=account, symbol=symbol, trader=trader, calculator=calculator, state_manager=state_manager)
            holidays = load_holiday_calendar(config.holiday_calendar)
            strategy.set_holidays(holidays)
            strategies.append(strategy)
        except Exception as e:
            logger.exception(f"Failed to load strategy from '{item.name}': {e}")
    return strategies