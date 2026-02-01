import logging
from app.common.services.dashboard_manager import DashboardManager
from app.common.config.paths import DASHBOARD_PATH

logger = logging.getLogger(__name__)

def get_dashboard_manager(dashboard_path: str = str(DASHBOARD_PATH)) -> DashboardManager:
    logger.info(f"Initializing DashboardManager at: {dashboard_path}")

    dashboard_manager = DashboardManager(dashboard_path)
    return dashboard_manager
