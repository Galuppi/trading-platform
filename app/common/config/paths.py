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

#dashboard files
DASHBOARD_PATH = ROOT_WWW / "status_dashboard.html"

#backtest directories and files
DATA_PATH = ROOT_DIR / "historical-data"
RESULT_PATH = ROOT_DIR / "backtest-results"
SUMMARY_PATH = ROOT_DIR / "backtest-results" / "backtest_summary.json"

#external urls
NEWS_URL = "https://nfs.faireconomy.media/ff_calendar_thisweek.csv"
