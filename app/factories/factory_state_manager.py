"""Builds the StateManager instance."""

import logging
from app.base.base_account import Account
from app.common.services.state_manager import StateManager
from app.common.config.paths import STATE_PATH

logger = logging.getLogger(__name__)


def get_state_manager(account: Account) -> StateManager:
    logger.info(f"Initializing StateManager at: {STATE_PATH}")

    state_manager = StateManager(
        state_path=STATE_PATH,
        account=account,
        persist_enabled=True,
    )
    return state_manager
