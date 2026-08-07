"""cTrader implementation of the Symbol interface."""

import logging
from typing import Any

from app.base.base_symbol import Symbol
from app.common.models.model_symbol import Range
from app.common.config.constants import (
    TIMEFRAME_M1,
    TIMEFRAME_M5,
    TIMEFRAME_M15,
    TIMEFRAME_M30,
    TIMEFRAME_H1,
    TIMEFRAME_H4,
    TIMEFRAME_D1,
)
from app.common.services.platform_time import PlatformTime
from app.connectors.ctrader.ctrader_session import CTraderSession, PRICE_SCALE

logger = logging.getLogger(__name__)

# ProtoOATrendbarPeriod enum values (see OpenApiModelMessages_pb2).
TIMEFRAME_MAP = {
    TIMEFRAME_M1: 1,
    TIMEFRAME_M5: 5,
    TIMEFRAME_M15: 7,
    TIMEFRAME_M30: 8,
    TIMEFRAME_H1: 9,
    TIMEFRAME_H4: 10,
    TIMEFRAME_D1: 12,
}


class CTraderSymbol(Symbol):
    """cTrader implementation of the Symbol interface."""

    def __init__(self):
        self.session = CTraderSession.instance()

    def get_ask_price(self, symbol: str) -> float:
        spot = self.session.get_spot(symbol)
        if spot.ask is None:
            raise ValueError(f"No ask price available yet for {symbol}")
        return spot.ask

    def get_bid_price(self, symbol: str) -> float:
        spot = self.session.get_spot(symbol)
        if spot.bid is None:
            raise ValueError(f"No bid price available yet for {symbol}")
        return spot.bid

    def is_valid_symbol(self, symbol: str) -> bool:
        try:
            light = self.session.get_light_symbol(symbol)
            return bool(light.enabled)
        except ValueError:
            return False

    def prepare_symbol(self, symbol: str) -> bool:
        try:
            self.session.ensure_subscribed(symbol)
            return True
        except Exception as error:
            logger.warning(f"Failed to prepare/subscribe cTrader symbol {symbol}: {error}")
            return False

    def get_symbol_info(self, symbol: str) -> Any:
        return self.session.get_symbol_details(symbol)

    def get_min_volume(self, symbol: str) -> float:
        info = self.session.get_symbol_details(symbol)
        return info.minVolume / info.lotSize

    def get_max_volume(self, symbol: str) -> float:
        info = self.session.get_symbol_details(symbol)
        return info.maxVolume / info.lotSize

    def get_volume_step(self, symbol: str) -> float:
        info = self.session.get_symbol_details(symbol)
        return info.stepVolume / info.lotSize

    def get_precision(self, symbol: str) -> int:
        info = self.session.get_symbol_details(symbol)
        return info.digits

    def get_contract_size(self, symbol: str) -> float:
        """Units per 1.0 lot, in real (non-scaled) units — mirrors MT5's trade_contract_size."""
        info = self.session.get_symbol_details(symbol)
        return info.lotSize / 100.0

    def get_tick_size(self, symbol: str) -> float:
        info = self.session.get_symbol_details(symbol)
        return 1 / (10 ** info.digits)

    def get_point_size(self, symbol: str) -> float:
        info = self.session.get_symbol_details(symbol)
        return 1 / (10 ** info.pipPosition)

    def get_currency_profit(self, symbol: str) -> str:
        light = self.session.get_light_symbol(symbol)
        return self.session.get_asset_name(light.quoteAssetId)

    def get_tick_value(self, symbol: str) -> float:
        """Value of one tick move for 1.0 lot, in the account's deposit currency.

        cTrader returns tick_size * contract_size in the symbol's own profit
        currency, unlike MT5's trade_tick_value which the broker already
        converts to the account currency. JPY-quoted pairs (EURJPY, USDJPY)
        are the current known case: profit currency JPY on a USD account,
        off by roughly the USDJPY rate if left unconverted. Converted here
        via the live USDJPY rate, since that pair is already actively traded
        and subscribed.
        """
        tick_size = self.get_tick_size(symbol)
        contract_size = self.get_contract_size(symbol)
        raw_tick_value = tick_size * contract_size

        if self.get_currency_profit(symbol) == "JPY":
            try:
                usdjpy_rate = self.get_bid_price("USDJPY")
            except Exception as error:
                logger.warning(f"Could not fetch USDJPY rate to convert tick value for {symbol}: {error}")
                return 0.0
            if usdjpy_rate <= 0:
                return 0.0
            return raw_tick_value / usdjpy_rate

        return raw_tick_value

    def get_high_low_range(
        self,
        symbol: str,
        start_minute: int,
        end_minute: int,
        timeframe: str = TIMEFRAME_M1,
    ) -> Range:
        now = PlatformTime.now()
        start_time = (
            now.replace(hour=0, minute=0, second=0, microsecond=0)
            + PlatformTime.timedelta(minutes=start_minute)
        )
        end_time = now.replace(hour=0, minute=0, second=0, microsecond=0) + PlatformTime.timedelta(minutes=end_minute)

        if start_time >= end_time:
            raise ValueError("Start time must be before end time")

        # PlatformTime.now() is broker-rollover-aligned wall clock, not true
        # UTC -- its wall-clock value is already shifted by
        # PlatformTime.get_offset() hours even though its tzinfo still claims
        # UTC. That's correct for the .replace()/comparisons above, but
        # .timestamp() trusts the tzinfo label, so the shift must be undone
        # here before building a real UTC epoch for the wire -- cTrader's
        # trendbar API wants genuine UTC milliseconds.
        offset_hours = PlatformTime.get_offset()
        true_utc_start = start_time - PlatformTime.timedelta(hours=offset_hours)
        true_utc_end = end_time - PlatformTime.timedelta(hours=offset_hours)

        period_enum = TIMEFRAME_MAP.get(timeframe, TIMEFRAME_MAP[TIMEFRAME_M1])
        from_ts_ms = int(true_utc_start.timestamp() * 1000)
        to_ts_ms = int(true_utc_end.timestamp() * 1000)

        bars = self.session.get_trendbars(symbol, period_enum, from_ts_ms, to_ts_ms)
        if not bars:
            raise RuntimeError(f"Failed to retrieve data for {symbol} from {start_time} to {end_time}")

        highs = [(bar.low + bar.deltaHigh) / PRICE_SCALE for bar in bars]
        lows = [bar.low / PRICE_SCALE for bar in bars]

        return Range(
            symbol=symbol,
            high=max(highs),
            low=min(lows),
            date=PlatformTime.today(),
        )

    def get_open_price(self, symbol: str) -> float:
        """Return the open price from the most recent M1 bar (today's opening price in practice)."""
        now = PlatformTime.now()
        offset_hours = PlatformTime.get_offset()
        true_utc_now = now - PlatformTime.timedelta(hours=offset_hours)
        from_ts_ms = int((true_utc_now - PlatformTime.timedelta(minutes=5)).timestamp() * 1000)
        to_ts_ms = int(true_utc_now.timestamp() * 1000)

        bars = self.session.get_trendbars(symbol, TIMEFRAME_MAP[TIMEFRAME_M1], from_ts_ms, to_ts_ms)
        if not bars:
            logger.warning(f"No M1 trendbars available for {symbol}")
            return None

        latest_bar = max(bars, key=lambda bar: bar.utcTimestampInMinutes)
        return (latest_bar.low + latest_bar.deltaOpen) / PRICE_SCALE
