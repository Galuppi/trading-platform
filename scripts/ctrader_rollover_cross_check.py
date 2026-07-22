"""Read-only diagnostic: compare the broker's CONFIGURED schedule rollover
hour against the ACTUALLY OBSERVED D1 candle open hour, to check whether
the schedule metadata is a faithful reflection of live behavior or not.

Usage:
    python -m scripts.ctrader_rollover_cross_check
"""

import time

from dotenv import load_dotenv

load_dotenv()

from app.common.config.loaders.loader_connector_config import load_connector_config
from app.common.services.platform_time import PlatformTime
from app.factories.factory_platform import get_connector, get_account
from app.factories.factory_state_manager import get_state_manager
from zoneinfo import ZoneInfo

TRENDBAR_PERIOD_D1 = 12


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

    session = connector.session

    print("\n=== CONFIGURED (schedule metadata) ===")
    details = session.get_symbol_details("EURUSD")
    schedule_hour = account._get_rollover_hour_of_day("EURUSD")  # private method, diagnostic use only
    print(f"scheduleTimeZone: {details.scheduleTimeZone}")
    print(f"Configured rollover hour of day (local): {schedule_hour}:00")

    schedule_tz = ZoneInfo(details.scheduleTimeZone)
    now_local = PlatformTime.local_now_utc().astimezone(schedule_tz)
    rollover_local = PlatformTime.replace(now_local, hour=schedule_hour, minute=0, second=0, microsecond=0)
    rollover_utc = PlatformTime.to_utc(rollover_local)
    print(f"Configured rollover, converted to UTC hour: {rollover_utc.hour}:00")

    print("\n=== OBSERVED (actual D1 candle data) ===")
    now = time.time()
    from_timestamp_ms = int((now - 5 * 86400) * 1000)
    to_timestamp_ms = int(now * 1000)
    bars = session.get_trendbars("EURUSD", TRENDBAR_PERIOD_D1, from_timestamp_ms, to_timestamp_ms)

    if not bars:
        print("No D1 bars returned.")
        return

    for bar in sorted(bars, key=lambda b: b.utcTimestampInMinutes):
        total_minutes = bar.utcTimestampInMinutes
        hour = (total_minutes // 60) % 24
        minute = total_minutes % 60
        print(f"  D1 bar open (UTC): {hour:02d}:{minute:02d}")

    print("\n=== COMPARISON ===")
    print(f"Configured says rollover at {rollover_utc.hour}:00 UTC.")
    print("Compare against the observed D1 bar open hours above — do they match?")


if __name__ == "__main__":
    main()
