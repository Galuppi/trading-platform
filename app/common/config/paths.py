"""Central definitions of filesystem paths used throughout the application."""

from pathlib import Path

#app root directories
ROOT_DIR = Path(__file__).resolve().parents[3]
ROOT_WWW = Path(r"C:\inetpub\wwwroot")

#app directories and files
APP_DIR = ROOT_DIR / "app"
STRATEGY_PATH = APP_DIR / "strategies"
STATE_PATH = APP_DIR / "runtime" / "state" / "state.json"
LOG_PATH = APP_DIR / "runtime" / "logs"
HOLIDAY_PATH = APP_DIR / "common" / "config" / "holidays" / "holidays_{}.yaml"
ACCOUNT_RISK_PATH = APP_DIR / "common" / "config" / "account_risk.yaml"

#lock file
LOCK_FILE_PATH = APP_DIR / "runtime" / "trader.lck"

#dashboard files
DASHBOARD_PATH = ROOT_WWW / "ctrader_status_dashboard.html"

#external urls
NEWS_URL = "https://nfs.faireconomy.media/ff_calendar_thisweek.csv"
VIX_FEED_PATH = r"C:\Apps\SignalProvider\signals\signals.json"
