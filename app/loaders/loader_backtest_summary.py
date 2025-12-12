import logging
from app.common.system.backtest_summary import BacktestSummary
from app.common.config.paths import SUMMARY_PATH

logger = logging.getLogger(__name__)

def load_backtest_summary(backtest_config):
    logger.info(f"Initializing BacktestSummary at: {SUMMARY_PATH}")

    summary_writer = BacktestSummary(backtest_config=backtest_config)
    return summary_writer
