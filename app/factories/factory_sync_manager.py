"""Builds the SyncManager instance."""

import logging
from app.common.services.sync_manager import SyncManager
from app.common.services.state_manager import StateManager
from app.common.services.pushover_manager import PushoverManager

logger = logging.getLogger(__name__)

def get_sync_manager(
    state_manager: StateManager,
    notify_manager: PushoverManager,
) -> SyncManager:
    logger.info("Initializing SyncManager")
    manager = SyncManager(
        state_manager=state_manager,
        notify_manager=notify_manager,
    )
    
    return manager