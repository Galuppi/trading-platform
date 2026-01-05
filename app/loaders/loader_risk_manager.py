import logging

from app.common.system.risk_manager import RiskManager

logger = logging.getLogger(__name__)


def load_risk_manager() -> RiskManager:
    logger.info("Initializing RiskManager")
    manager = RiskManager()
    manager.initialize()
    return manager