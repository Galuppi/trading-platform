"""cTrader implementation of the Account interface."""

import logging
from typing import List, Optional
from zoneinfo import ZoneInfo

from app.base.base_account import Account
from app.common.models.model_trade import OrderRequest, TradeRecord
from app.common.config.constants import (
    TRADE_DIRECTION_BUY,
    TRADE_STATUS_CLOSED,
    DATETIME_FORMAT,
    TIME_REFERENCE_SYMBOL,
)
from app.common.services.platform_time import PlatformTime
from app.connectors.ctrader.ctrader_session import CTraderSession, PRICE_SCALE

logger = logging.getLogger(__name__)

# ProtoOATradeSide enum values.
TRADE_SIDE_BUY = 1
TRADE_SIDE_SELL = 2

# ProtoOAPositionStatus enum values.
POSITION_STATUS_OPEN = 1


class CTraderAccount(Account):
    """cTrader implementation of the Account interface."""

    def __init__(self):
        self.session = CTraderSession.instance()

    def _money(self, raw: int, money_digits: int) -> float:
        return raw / (10 ** money_digits) if money_digits else raw / 100.0

    def get_balance(self) -> float:
        trader = self.session.get_trader()
        return self._money(trader.balance, trader.moneyDigits)

    def get_equity(self) -> float:
        trader = self.session.get_trader()
        balance = self._money(trader.balance, trader.moneyDigits)
        pnl_entries = self.session.get_unrealized_pnl()
        unrealized = sum(self._money(p.netUnrealizedPnL, trader.moneyDigits) for p in pnl_entries)
        return balance + unrealized

    def set_balance(self, new_balance: float) -> None:
        # Only meaningful on demo accounts, and not exposed as a standard Open
        # API trading call (it's a cTrader web/desktop UI action). No-op, same
        # as MT5's implementation in this codebase.
        pass

    def set_equity(self, new_equity: float) -> None:
        pass

    def get_account_currency(self) -> str:
        trader = self.session.get_trader()
        return self.session.get_asset_name(trader.depositAssetId)

    def get_commission_per_lot(self) -> float:
        return 0.0

    def get_slippage_per_lot(self) -> float:
        return 0.0

    def get_free_margin(self, symbol: str) -> float:
        equity = self.get_equity()
        reconcile = self.session.reconcile()
        trader = self.session.get_trader()
        used_margin = sum(self._money(pos.usedMargin, trader.moneyDigits) for pos in reconcile.position)
        return equity - used_margin

    def get_margin_required(self, order: OrderRequest) -> float:
        api_volume = self.session.lots_to_api_volume(order.symbol, order.lot_size)
        response = self.session.get_expected_margin(order.symbol, api_volume)
        if not response.margin:
            return 0.0
        margin_entry = response.margin[0]
        raw_margin = margin_entry.buyMargin if order.direction == TRADE_DIRECTION_BUY else margin_entry.sellMargin
        return self._money(raw_margin, response.moneyDigits)

    def has_sufficient_margin(self, order: OrderRequest) -> bool:
        try:
            margin_required = self.get_margin_required(order)
            free_margin = self.get_free_margin(order.symbol)
            return margin_required <= free_margin
        except Exception as e:
            logger.warning(f"Margin check failed for {order.symbol} (lot size {order.lot_size}): {e}", exc_info=True)
            return False

    def get_account_number(self) -> int:
        return self.session.ctid_trader_account_id or 0

    def get_open_tickets(self) -> List[str]:
        reconcile = self.session.reconcile()
        return [
            str(pos.positionId)
            for pos in reconcile.position
            if pos.positionStatus == POSITION_STATUS_OPEN
        ]

    def get_closed_tickets(self, lookback_hours: int = 24) -> List[TradeRecord]:
        now = PlatformTime.now()
        # See ctrader_symbol.get_high_low_range() for why this offset
        # correction is needed before calling .timestamp().
        true_utc_now = now - PlatformTime.timedelta(hours=PlatformTime.get_offset())
        start_ms = int((true_utc_now - PlatformTime.timedelta(hours=lookback_hours)).timestamp() * 1000)
        end_ms = int((true_utc_now + PlatformTime.timedelta(hours=lookback_hours)).timestamp() * 1000)

        deals = self.session.deal_list(start_ms, end_ms)

        closed_tickets = []
        for deal in deals:
            if not deal.HasField("closePositionDetail") or deal.volume <= 0:
                continue

            light_symbol = self.session._symbols_by_id.get(deal.symbolId)
            symbol_name = light_symbol.symbolName if light_symbol else str(deal.symbolId)
            money_digits = deal.moneyDigits or deal.closePositionDetail.moneyDigits

            lot_size = self.session._symbol_details_by_id.get(deal.symbolId)
            volume_lots = deal.volume / lot_size.lotSize if lot_size else deal.volume / 10000000.0

            trade = TradeRecord(
                id=str(deal.positionId),
                symbol=symbol_name,
                lot_size=volume_lots,
                type="buy" if deal.tradeSide == TRADE_SIDE_BUY else "sell",
                ticket=str(deal.positionId),
                status=TRADE_STATUS_CLOSED,
                timestamp=PlatformTime.datetime_str(),
                strategy="external",
                entry_price=deal.closePositionDetail.entryPrice,
                exit_price=deal.executionPrice,
                exit_time=PlatformTime.from_timestamp(deal.executionTimestamp / 1000).strftime(DATETIME_FORMAT),
                stop_loss=None,
                stop_loss_points=None,
                take_profit=None,
                commission=self._money(deal.commission, money_digits),
                comment="",
                profit=self._money(deal.closePositionDetail.grossProfit, money_digits),
                slippage_entry=None,
            )
            closed_tickets.append(trade)

        return closed_tickets

    def get_server_offset_hours(self) -> Optional[float]:
        """Return the offset that aligns midnight with the broker's actual configured rollover."""
        details = self.session.get_symbol_details(TIME_REFERENCE_SYMBOL)
        schedule_timezone_name = details.scheduleTimeZone
        rollover_hour = self._get_rollover_hour_of_day(TIME_REFERENCE_SYMBOL)
        if not schedule_timezone_name or rollover_hour is None:
            return 0

        schedule_timezone = ZoneInfo(schedule_timezone_name)
        now_local = PlatformTime.local_now_utc().astimezone(schedule_timezone)
        rollover_local = PlatformTime.replace(now_local, hour=rollover_hour, minute=0, second=0, microsecond=0)
        rollover_utc = PlatformTime.to_utc(rollover_local)
        return float((24 - rollover_utc.hour) % 24)

    def _get_rollover_hour_of_day(self, symbol: str) -> Optional[int]:
        """Return the broker's configured daily rollover hour, in the symbol's own scheduleTimeZone."""
        details = self.session.get_symbol_details(symbol)
        if not details.schedule:
            return None
        seconds_since_midnight = details.schedule[0].startSecond % 86400
        return round(seconds_since_midnight / 3600) % 24

    def get_server_tick_timestanp(self) -> Optional[int]:
        """Return a value that changes every call, so the engine always recomputes the offset.

        cTrader's spot event for a non-traded reference symbol can freeze at
        a placeholder timestamp (Spotware sends a "technical" first event on
        subscription that isn't a real tick). Rather than depend on that,
        this uses wall-clock time directly — safe because
        get_server_offset_hours() is cheap (cached schedule data, no network
        call), unlike MT5's live tick read, so there's no cost to always
        recomputing.
        """
        return int(PlatformTime.local_now_utc().timestamp())
