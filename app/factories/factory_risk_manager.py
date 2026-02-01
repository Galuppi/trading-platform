import logging

from app.common.services.risk_manager import RiskManager

logger = logging.getLogger(__name__)


def get_risk_manager() -> RiskManager:
    logger.info("Initializing RiskManager")
    manager = RiskManager()
    manager.initialize()
    return manager