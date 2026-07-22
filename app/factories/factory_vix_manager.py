"""Builds the VixManager instance."""

import logging

from app.common.services.vix_manager import VixManager

logger = logging.getLogger(__name__)


def get_vix_manager() -> VixManager:
    """Construct a new VixManager."""
    logger.info("Initializing VixManager")
    return VixManager()
