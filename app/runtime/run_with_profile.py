import cProfile
import pstats
import logging
from dotenv import load_dotenv

load_dotenv()

from app.common.config.paths import STATE_PATH, LOG_PATH
from app.common.config.constants import MODE_BACKTEST
from app.common.system.state_manager import StateManager
from app.common.system.logger import setup_logger
from app.loaders.loader_connector_config import load_connector_config
from app.loaders.loader_backtest_config import load_backtest_config
from app.loaders.loader_platform import (
    get_connector,
    get_account,
    get_trade,
    get_symbol,
    get_calculator,
)
from app.loaders.loader_strategy import strategy_registry
from app.runtime.engine import Engine
from app.runtime.enginetester import EngineTester
from app.loaders.loader_timestamp import load_tester_setup
from app.common.system.backtest_summary import BacktestSummary
from app.common.system.platform_time import PlatformTime

logger = logging.getLogger(__name__)

def profiled_main():
    connector_config = load_connector_config()
    backtester_config = load_backtest_config()

    setup_logger(LOG_PATH, connector_config.mode)
    logger.info(f"Using state file: {STATE_PATH}")

    PlatformTime.set_timezone(connector_config.timezone or "UTC")
    PlatformTime.set_mode(connector_config.mode)

    platform_name = (connector_config.type or "").lower()
    is_backtest = connector_config.mode == MODE_BACKTEST
    persist_enabled = bool(backtester_config.backtest_persist) if is_backtest else True

    account = get_account(platform_name, backtester_config)
    state_manager = StateManager(STATE_PATH, account, persist_enabled)
    summary_writer = BacktestSummary(backtester_config)

    connector = get_connector(platform_name, connector_config)
    if not connector.connect():
        logger.error("Failed to connect to trading platform.")
        raise RuntimeError("Platform connection failed.")

    symbol = get_symbol(platform_name, backtester_config, account)
    calculator = get_calculator(platform_name, symbol, account, backtester_config)
    trade = get_trade(platform_name, symbol, calculator, summary_writer)

    strategies = strategy_registry(
        connector=connector,
        account=account,
        symbol=symbol,
        trader=trade,
        calculator=calculator,
        state_manager=state_manager,
    )

    if is_backtest:
        test_period, timestamps = load_tester_setup()
        app = EngineTester(
            strategies=strategies,
            state_manager=state_manager,
            simulation_timestamps=timestamps.values,
            summary_writer=summary_writer,
            connector_config=connector_config,
            backtester_config=backtester_config,
        )
    else:
        app = Engine(
            strategies=strategies,
            state_manager=state_manager,
            connector_config=connector_config,
            backtester_config=backtester_config,
        )

    app.run()

if __name__ == "__main__":
    try:
        profile_path = "profile.prof"
        cProfile.run("profiled_main()", profile_path)
        print(f"✅ Profile written to: {profile_path}")

        # Optional: print top 20 results
        stats = pstats.Stats(profile_path)
        stats.strip_dirs().sort_stats("time").print_stats(20)

    except Exception as e:
        logger.exception(f"Fatal error: {e}")
        input("Press Enter to exit...")
