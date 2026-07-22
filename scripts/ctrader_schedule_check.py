"""Read-only diagnostic: print EURUSD's raw schedule intervals and
scheduleTimeZone, to decode the exact startSecond/endSecond convention
against the real session hours shown in the cTrader UI.

Usage:
    python -m scripts.ctrader_schedule_check
"""

from dotenv import load_dotenv

load_dotenv()

from app.common.config.loaders.loader_connector_config import load_connector_config
from app.common.services.platform_time import PlatformTime
from app.factories.factory_platform import get_connector, get_account
from app.factories.factory_state_manager import get_state_manager

WEEKDAY_NAMES = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]


def seconds_to_weekday_time(total_seconds: int) -> str:
    day_index = total_seconds // 86400
    remainder = total_seconds % 86400
    hour = remainder // 3600
    minute = (remainder % 3600) // 60
    second = remainder % 60
    day_name = WEEKDAY_NAMES[day_index % 7]
    return f"{day_name} {hour:02d}:{minute:02d}:{second:02d}"


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
    details = session.get_symbol_details("EURUSD")

    print(f"\nscheduleTimeZone: {details.scheduleTimeZone!r}\n")
    print("Raw schedule intervals (assuming seconds since start of week):")
    for interval in details.schedule:
        start = seconds_to_weekday_time(interval.startSecond)
        end = seconds_to_weekday_time(interval.endSecond)
        print(f"  startSecond={interval.startSecond:>7}  ({start})")
        print(f"  endSecond=  {interval.endSecond:>7}  ({end})")
        print()


if __name__ == "__main__":
    main()
