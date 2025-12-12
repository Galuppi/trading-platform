import MetaTrader5 as mt5
import logging

from typing import List, Optional
from app.base.base_account import Account
from app.common.models.model_trade import OrderRequest, TradeRecord
from app.common.config.constants import (
    TRADE_DIRECTION_BUY,
    TRADE_STATUS_CLOSED,
    DATETIME_FORMAT,
    TIME_REFERENCE_SYMBOL,
    RETRY_COUNT,
    RETRY_DELAY_SECONDS,
    )
from app.common.system.platform_time import PlatformTime

logger = logging.getLogger(__name__)


class Mt5Account(Account):
    def get_balance(self) -> float:
        account_info = self._safe_account_info()
        if account_info is None:
            return 0.0
        return account_info.balance

    def get_equity(self) -> float:
        account_info = self._safe_account_info()
        if account_info is None:
            return 0.0
        return account_info.equity
    
    def get_account_currency(self) -> str:
        account_info = self._safe_account_info()
        if account_info is None:
            return 0.0
        return account_info.currency

    def get_commission_per_lot(self) -> float:
        return 0.0

    def get_free_margin(self, symbol: str) -> float:
        account_info = self._safe_account_info()
        if account_info is None:
            return 0.0
        return account_info.margin_free

    def get_margin_required(self, order: OrderRequest) -> float:
        price = mt5.symbol_info_tick(order.symbol).ask
        result = mt5.order_calc_margin(
            mt5.ORDER_TYPE_BUY if order.direction == TRADE_DIRECTION_BUY else mt5.ORDER_TYPE_SELL,
            order.symbol,
            order.lot_size,
            price
        )
        if result is None or result < 0:
            raise ValueError(f"Failed to calculate margin for {order.symbol}")
        return result


    def has_sufficient_margin(self, order: OrderRequest) -> bool:
        try:
            margin_required = self.get_margin_required(order)
            free_margin = self.get_free_margin(order.symbol)
            return margin_required <= free_margin
        except Exception as e:
            logger.warning(
                f"Margin check failed for {order.symbol} (lot size {order.lot_size}): {e}"
            )
            return False

    def get_account_number(self) -> int:
        account_info = self._safe_account_info()
        if account_info is None:
            return 0.0
        return account_info.login
    
    def get_open_tickets(self) -> List[str]:
        positions = mt5.positions_get()
        if positions is None:
            return []
        return [str(pos.ticket) for pos in positions]

    def get_closed_tickets(self, lookback_hours: int = 24) -> List[TradeRecord]:
            now = PlatformTime.now()
            start = now - PlatformTime.timedelta(hours=lookback_hours)
            end = now + PlatformTime.timedelta(hours=lookback_hours)

            _ = mt5.history_orders_get(start, end)
            deals = mt5.history_deals_get(start, end)
            if not deals:
                return []

            closed_tickets = []
            for d in deals:
                deal = d._asdict()

                if (
                    not deal.get("symbol")
                    or float(deal.get("volume", 0)) <= 0
                    or deal.get("entry") != mt5.DEAL_ENTRY_OUT
                ):
                    continue

                if deal.get("entry") != mt5.DEAL_ENTRY_OUT:
                    continue

                trade = TradeRecord(
                    id=str(deal["position_id"]),
                    symbol=deal["symbol"],
                    lot_size=float(deal["volume"]),
                    type="buy" if deal["type"] in (mt5.DEAL_TYPE_BUY, mt5.ORDER_TYPE_BUY) else "sell",
                    ticket=str(deal["position_id"]),
                    status=TRADE_STATUS_CLOSED,
                    timestamp=PlatformTime.datetime_str(),
                    strategy="external",
                    entry_price=None,
                    exit_price=float(deal.get("price", 0.0)),
                    exit_time=PlatformTime.from_timestamp(deal["time"]).strftime(DATETIME_FORMAT),
                    stop_loss=None,
                    stop_loss_points=None,
                    take_profit=None,
                    commission=float(deal.get("commission", 0.0)),
                    comment=str(deal.get("comment", "")),
                    profit=float(deal.get("profit", 0.0)),
                    slippage_entry=None,
                )

                closed_tickets.append(trade)

            return closed_tickets
    
    def get_server_offset_hours(self) -> Optional[int]:
        tick = mt5.symbol_info_tick(TIME_REFERENCE_SYMBOL)   
        if not tick:
            return None
        
        broker_time = PlatformTime.from_timestamp(tick.time, is_utc=True)

        utc_now = PlatformTime.local_now_utc()

        offset_hours = (broker_time - utc_now).total_seconds() / 3600
        offset_int = int(round(offset_hours))

        return offset_int
    
    def _safe_account_info(self):
        for attempt in range(1, RETRY_COUNT + 1):
            info = mt5.account_info()
            if info is not None:
                return info

            logger.warning(f"[Attempt {attempt}/{RETRY_COUNT}] Failed to retrieve account info. Retrying...")
            PlatformTime.sleep(RETRY_DELAY_SECONDS)

        logger.error("Unable to retrieve account info after retries. Broker connection likely down.")
        return None

    def get_server_tick_timestanp(self) -> Optional[int]:
        tick = mt5.symbol_info_tick(TIME_REFERENCE_SYMBOL)   
        if not tick:
            return None
        
        return tick.time