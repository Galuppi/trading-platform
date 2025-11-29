from typing import Any

from pathlib import Path
ROOT_DIR = Path(__file__).resolve().parents[3]
ROOT_WWW = Path('C:\\inetpub\\wwwroot')
APP_DIR = ROOT_DIR / 'app'
DASHBOARD_PATH = ROOT_WWW / 'status_dashboard.html'
CONFIG_PATH = APP_DIR / 'config' / 'config.yaml'
STATE_PATH = APP_DIR / 'runtime' / 'state' / 'state.json'
LOG_PATH = APP_DIR / 'runtime' / 'logs'
STRATEGY_PATH = APP_DIR / 'strategies'
DATA_PATH = ROOT_DIR / 'historical-data'
RESULT_PATH = ROOT_DIR / 'backtest-results'
SUMMARY_PATH = ROOT_DIR / 'backtest-results' / 'backtest_summary.json'
HOLIDAY_PATH = APP_DIR / 'common' / 'holidays' / 'holidays_{}.yaml'