"""Application entry point — wires up and runs the live trading engine."""

import logging
import sys

from dotenv import load_dotenv

from app.factories.factory_calculator import get_calculator

load_dotenv()

from app.common.config.paths import STATE_PATH, LOG_PATH, LOCK_FILE_PATH
from app.common.config.constants import ENVIRONMENT_PRODUCTION
from app.common.services.logger import setup_logger
from app.common.config.loaders.loader_connector_config import load_connector_config
from app.common.config.loaders.loader_notify_config import load_notify_config
from app.factories.factory_platform import (
    get_connector,
    get_account,
    get_trade,
    get_symbol,
)
from app.factories.factory_strategy import strategy_registry
from app.runtime.engine import Engine
from app.common.services.platform_time import PlatformTime
from app.factories.factory_state_manager import get_state_manager
from app.factories.factory_dashboard_manager import get_dashboard_manager
from app.factories.factory_news_manager import get_news_manager
from app.factories.factory_risk_manager import get_risk_manager
from app.factories.factory_vix_manager import get_vix_manager
from app.factories.factory_notify_manager import get_notify_manager
from app.factories.factory_sync_manager import get_sync_manager

logger = logging.getLogger(__name__)


def is_already_running(environment: str) -> bool:
    if LOCK_FILE_PATH.exists() and environment == ENVIRONMENT_PRODUCTION:
        print("Another instance is already running. Exiting.")
        return True
    else:
        LOCK_FILE_PATH.touch()
        return False


if __name__ == "__main__":

    connector_config = load_connector_config()

    if is_already_running(connector_config.environment):
        sys.exit(1)

    notify_config = load_notify_config()

    platform_name = (connector_config.type or "").lower()

    setup_logger(LOG_PATH, connector_config.environment)
    logger.info(f"Environment: {connector_config.environment} | Platform: {platform_name} | Server: {connector_config.server}")
    logger.info(f"Using state file: {STATE_PATH}")

    PlatformTime.set_timezone(connector_config.timezone or "UTC")
    PlatformTime.set_offset(connector_config.offset or 0)

    account = get_account(platform_name)
    symbol = get_symbol(platform_name)
    state_manager = get_state_manager(account)
    dashboard = get_dashboard_manager()
    news_manager = get_news_manager(window_minutes=30)
    risk_manager = get_risk_manager()
    vix_manager = get_vix_manager()
    notify_manager = get_notify_manager(notify_config)
    calculator = get_calculator(symbol, account)
    trade = get_trade(platform_name, symbol, calculator)
    sync_manager = get_sync_manager(state_manager, notify_manager)

    connector = get_connector(platform_name, connector_config, state_manager)
    if not connector.connect():
        logger.error("Failed to connect to trading platform.")
        raise RuntimeError("Platform connection failed.")

    logger.info(f"Connected: Account #{connector_config.login}, Server: {connector_config.server}")

    strategies = strategy_registry(
        connector=connector,
        account=account,
        symbol=symbol,
        trader=trade,
        calculator=calculator,
        state_manager=state_manager,
        news_manager=news_manager,
        risk_manager=risk_manager,
        vix_manager=vix_manager,
        notify_manager=notify_manager,
    )

    app = Engine(
        connector=connector,
        account=account,
        strategies=strategies,
        state_manager=state_manager,
        connector_config=connector_config,
        dashboard_manager=dashboard,
        news_manager=news_manager,
        vix_manager=vix_manager,
        risk_manager=risk_manager,
        notify_manager=notify_manager,
        sync_manager=sync_manager,
    )

    try:
        app.run()
    except KeyboardInterrupt:
        logger.info("Interrupted by user — shutting down.")
    except Exception as e:
        logger.exception(f"Fatal error: {e}")
        input("Press Enter to exit...")
    finally:
        try:
            if LOCK_FILE_PATH.exists():
                LOCK_FILE_PATH.unlink()
        except Exception:
            pass
