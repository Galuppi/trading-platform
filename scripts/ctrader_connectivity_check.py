"""One-off sanity check: connect to cTrader via the real connector stack and
print account info + open positions. Does NOT run the strategy engine —
this only exercises connect(), account balance/equity, and open tickets, so
a mistake here can't place or touch any trades.

Usage:
    python scripts/ctrader_connectivity_check.py

Requires PLATFORM_TYPE=ctrader and PLATFORM_ENVIRONMENT=Development in .env
(Development -> demo host, Production -> live host), plus the CTRADER_*
credentials already set.
"""

import logging
import sys

from dotenv import load_dotenv

load_dotenv()

from app.common.config.loaders.loader_connector_config import load_connector_config
from app.common.services.platform_time import PlatformTime
from app.factories.factory_platform import get_connector, get_account
from app.factories.factory_state_manager import get_state_manager

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger(__name__)


def main() -> None:
    config = load_connector_config()

    if config.type != "ctrader":
        print(f"PLATFORM_TYPE is '{config.type}', expected 'ctrader'. Update .env and retry.")
        sys.exit(1)

    PlatformTime.set_timezone(config.timezone or "UTC")
    PlatformTime.set_offset(config.offset or 0)

    print(f"Connecting to cTrader ({config.environment})...")
    account = get_account(config.type)
    state_manager = get_state_manager(account)
    connector = get_connector(config.type, config, state_manager)

    if not connector.connect():
        print("Connection failed. Check the logs above for the specific error.")
        sys.exit(1)

    print("Connected successfully.\n")

    print("=== Account info ===")
    print(f"Account number:     {account.get_account_number()}")
    print(f"Account currency:   {account.get_account_currency()}")
    print(f"Balance:            {account.get_balance()}")
    print(f"Equity:             {account.get_equity()}")

    open_tickets = account.get_open_tickets()
    print(f"\nOpen positions:     {len(open_tickets)}")
    for ticket in open_tickets:
        print(f"  - {ticket}")

    offset = account.get_server_offset_hours()
    print(f"\nSchedule timezone offset (hours): {offset}")

    print("\nAll good.")


if __name__ == "__main__":
    main()