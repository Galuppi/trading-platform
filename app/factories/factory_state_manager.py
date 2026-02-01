import logging
from app.common.services.state_manager import StateManager
from app.common.config.paths import STATE_PATH
from app.common.config.constants import MODE_BACKTEST

logger = logging.getLogger(__name__)

def get_state_manager(account, connector_config, backtester_config):

    is_backtest = connector_config.mode == MODE_BACKTEST
    persist_enabled = bool(backtester_config.backtest_persist) if is_backtest else True

    logger.info(f"Initializing StateManager at: {STATE_PATH}")
    logger.debug(f"Persistence enabled: {persist_enabled}, Backtest mode: {is_backtest}")

    state_manager = StateManager(
        state_path=STATE_PATH,
        account=account,
        persist_enabled=persist_enabled,
    )
    return state_manager
