import logging

from dotenv import load_dotenv

from app.factories.factory_calculator import get_calculator

load_dotenv()

from app.common.config.paths import STATE_PATH, LOG_PATH
from app.common.config.constants import MODE_BACKTEST
from app.common.services.logger import setup_logger
from app.common.config.loaders.loader_connector_config import load_connector_config
from app.common.config.loaders.loader_backtest_config import load_backtest_config
from app.common.config.loaders.loader_notify_config import load_notify_config
from app.factories.factory_platform import (
    get_connector,
    get_account,
    get_trade,
    get_symbol,
)
from app.factories.factory_strategy import strategy_registry
from app.runtime.engine import Engine
from app.runtime.enginetester import EngineTester
from app.common.config.loaders.loader_timestamp import load_tester_setup
from app.common.services.platform_time import PlatformTime
from app.factories.factory_state_manager import get_state_manager
from app.factories.factory_backtest_summary import get_backtest_summary
from app.factories.factory_dashboard_manager import get_dashboard_manager
from app.factories.factory_news_manager import get_news_manager
from app.factories.factory_risk_manager import get_risk_manager
from app.factories.factory_notify_manager import get_notify_manager
from app.factories.factory_sync_manager import get_sync_manager

logger = logging.getLogger(__name__)

if __name__ == "__main__":

    connector_config = load_connector_config()
    backtester_config = load_backtest_config()
    notify_config = load_notify_config()

    platform_name = (connector_config.type or "").lower()
    is_backtest = connector_config.mode == MODE_BACKTEST

    setup_logger(LOG_PATH, connector_config.mode)
    logger.info(f"Using state file: {STATE_PATH}")

    PlatformTime.set_timezone(connector_config.timezone or "UTC")
    PlatformTime.set_offset(connector_config.offset or 0)
    PlatformTime.set_mode(connector_config.mode)
    
    account = get_account(platform_name, backtester_config)
    symbol = get_symbol(platform_name, backtester_config, account)
    state_manager = get_state_manager(account, connector_config, backtester_config)
    summary_writer = get_backtest_summary(backtester_config)
    dashboard = get_dashboard_manager()
    news_manager = get_news_manager(window_minutes=30)
    risk_manager = get_risk_manager()
    notify_manager = get_notify_manager(notify_config, is_backtest)
    calculator = get_calculator(symbol, account)
    trade = get_trade(platform_name, symbol, calculator, summary_writer)
    sync_manager = get_sync_manager(state_manager, notify_manager)
   
    connector = get_connector(platform_name, connector_config)
    if not connector.connect():
        logger.error("Failed to connect to trading platform.")
        raise RuntimeError("Platform connection failed.")

    logger.info(f"Connected to MT5: Account #{connector_config.login}, Server: {connector_config.server}")
    
    strategies = strategy_registry(
        connector=connector,
        account=account,
        symbol=symbol,
        trader=trade,
        calculator=calculator,
        state_manager=state_manager,
        news_manager=news_manager,
        risk_manager=risk_manager,
        notify_manager=notify_manager,
    )

    if is_backtest:
        test_period, timestamps = load_tester_setup()
        
        if timestamps.values:
            PlatformTime.set_backtest_timestamp(timestamps.values[0])

        app = EngineTester(
            connector=connector,
            account=account,
            strategies=strategies,
            state_manager=state_manager,
            simulation_timestamps=timestamps.values,
            summary_writer=summary_writer,
            connector_config=connector_config,
            backtester_config=backtester_config,
            dashboard_manager=dashboard,
            news_manager=news_manager,
            risk_manager=risk_manager,
            notify_manager=notify_manager,
            sync_manager=sync_manager,
        )
    else:
        app = Engine(
            connector=connector,
            account=account,
            strategies=strategies,
            state_manager=state_manager,
            connector_config=connector_config,
            backtester_config=backtester_config,
            dashboard_manager=dashboard,
            news_manager=news_manager,
            risk_manager=risk_manager,
            summary_writer=summary_writer,
            notify_manager=notify_manager,
            sync_manager=sync_manager,
        )

    try:
        app.run()
    except Exception as e:
        logger.exception(f"Fatal error: {e}")
        input("Press Enter to exit...")
