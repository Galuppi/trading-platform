"""Builds the DealArchiveManager instance."""

import logging
from pathlib import Path

from app.common.services.deal_archive_manager import DealArchiveManager

logger = logging.getLogger(__name__)


def get_deal_archive_manager(db_path: Path, platform: str, account_id: str) -> DealArchiveManager:
    """Builds a DealArchiveManager pointed at the given SQLite file."""
    logger.info(f"Initializing DealArchiveManager at: {db_path}")

    return DealArchiveManager(
        db_path=db_path,
        platform=platform,
        account_id=account_id,
    )
