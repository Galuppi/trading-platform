"""Read-only diagnostic: stay connected and print every SWAP execution event
as it happens, with its real UTC timestamp - genuine observed evidence of
when the broker actually applies swap, not a config value.

Leave this running through a rollover moment (e.g. overnight) on an account
with an open position on a 24/7 instrument (crypto) to catch one live.

Usage:
    python -m scripts.ctrader_swap_watch
"""

import time

from dotenv import load_dotenv

load_dotenv()

from app.common.config.loaders.loader_connector_config import load_connector_config
from app.common.services.platform_time import PlatformTime
from app.factories.factory_platform import get_connector, get_account
from app.factories.factory_state_manager import get_state_manager

EXECUTION_TYPE_SWAP = 9


def main() -> None:
    config = load_connector_config()
    PlatformTime.set_timezone(config.timezone or "UTC")
    PlatformTime.set_offset(0)

    account = get_account(config.type)
    state_manager = get_state_manager(account)
    connector = get_connector(config.type, config, state_manager)

    if not connector.connect():
        print("Connection failed.")
        return

    def on_execution_event(event) -> None:
        if event.executionType != EXECUTION_TYPE_SWAP:
            return
        deal = event.deal if event.HasField("deal") else None
        position_id = event.position.positionId if event.HasField("position") else None
        swap_amount = deal.swap if deal else None
        timestamp_ms = deal.executionTimestamp if deal else None
        observed_utc = PlatformTime.from_timestamp(timestamp_ms / 1000, is_utc=True) if timestamp_ms else None
        print(f"\nSWAP event observed at real UTC time: {observed_utc}")
        print(f"  position: {position_id}, swap amount: {swap_amount}")

    connector.session.set_execution_event_callback(on_execution_event)

    print("Connected. Watching for SWAP execution events... (Ctrl+C to stop)")
    try:
        while True:
            time.sleep(60)
    except KeyboardInterrupt:
        print("\nStopped.")


if __name__ == "__main__":
    main()
