"""Read-only diagnostic: print raw open-position timestamps from the cTrader
API, converted to UTC, so they can be compared directly against what the
cTrader UI displays (which shows a "Created (UTC+2)" column). Does not place,
modify, or close anything.

Usage:
    python -m scripts.ctrader_timestamp_check
"""

from dotenv import load_dotenv

load_dotenv()

from app.common.config.loaders.loader_connector_config import load_connector_config
from app.common.services.platform_time import PlatformTime
from app.factories.factory_platform import get_connector


def main() -> None:
    config = load_connector_config()
    PlatformTime.set_timezone(config.timezone or "UTC")
    PlatformTime.set_offset(0)  # keep this raw/UTC for the comparison — no offset applied

    connector = get_connector(config.type, config)
    if not connector.connect():
        print("Connection failed.")
        return

    session = connector.session
    reconcile = session.reconcile()

    print("\n=== Open positions: raw API timestamp vs UTC ===")
    for pos in reconcile.position:
        open_ts_ms = pos.tradeData.openTimestamp
        symbol_id = pos.tradeData.symbolId
        light = session._symbols_by_id.get(symbol_id)
        symbol_name = light.symbolName if light else str(symbol_id)

        as_utc = PlatformTime.from_timestamp(open_ts_ms / 1000, is_utc=True)

        print(f"Position {pos.positionId} ({symbol_name}):")
        print(f"  raw openTimestamp (ms):  {open_ts_ms}")
        print(f"  interpreted as UTC:      {as_utc.strftime('%Y-%m-%d %H:%M:%S %Z')}")
        print()

    print("Compare the 'interpreted as UTC' values above against the cTrader UI's")
    print("'Created (UTC+2)' column, minus 2 hours. If they match, the API is")
    print("genuine UTC. If they match the UI value directly (no -2h needed),")
    print("the API is actually returning broker-local time.")


if __name__ == "__main__":
    main()
