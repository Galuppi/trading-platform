"""Builds the DealArchiveManager instance."""

import logging

from app.common.config.paths import DEALS_DB_PATH
from app.common.services.deal_archive_manager import DealArchiveManager

logger = logging.getLogger(__name__)

def get_deal_archive_manager(platform: str, account_id: str) -> DealArchiveManager:
    logger.info(f"Initializing DealArchiveManager at: {DEALS_DB_PATH}")

    deal_archive_manager = DealArchiveManager(
        db_path=DEALS_DB_PATH,
        platform=platform,
        account_id=account_id,
    )
    return deal_archive_manager
