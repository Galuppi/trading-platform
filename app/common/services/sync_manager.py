from typing import List, Any

from app.common.services.platform_time import PlatformTime
from app.common.config.constants import TRADE_STATUS_OPEN, TRADE_STATUS_CLOSED, DATETIME_FORMAT
from app.common.models.model_trade import TradeRecord
from app.common.services.state_manager import StateManager
from app.common.services.notify_manager import NotifyManager


class SyncManager:
    def __init__(
        self,
        state_manager: StateManager,
        notify_manager: NotifyManager,
    ) -> None:
        self.state_manager = state_manager
        self.notify_manager = notify_manager

    def sync_status_with_broker(self, open_ticket_ids: List[str]) -> None:
        open_ticket_ids_set = set(open_ticket_ids)
        for trade in self.state_manager.get_all_trades():
            if trade.status == TRADE_STATUS_OPEN and str(trade.ticket) not in open_ticket_ids_set:
                trade.status = TRADE_STATUS_CLOSED
                trade.exit_time = PlatformTime.now().strftime(DATETIME_FORMAT)
                trade.comment = "Closed externally"
                self.state_manager.add_trade(trade)

    def sync_tickets_with_broker(self, closed_tickets: List[TradeRecord]) -> None:
        if not closed_tickets:
            return
        closed_tickets_map = {str(t.ticket): t for t in closed_tickets}
        for trade in self.state_manager.get_all_trades():
            ticket = str(trade.ticket)
            broker_trade = closed_tickets_map.get(ticket)
            if not broker_trade:
                continue
            updated = False
            if (trade.exit_price is None or trade.exit_price == 0.0) and broker_trade.exit_price:
                trade.exit_price = broker_trade.exit_price
                updated = True
            if (trade.profit is None or trade.profit == 0.0) and broker_trade.profit:
                trade.profit = broker_trade.profit
                updated = True
            if (trade.commission is None or trade.commission == 0.0) and broker_trade.commission:
                trade.commission = broker_trade.commission
                updated = True
            if trade.slippage_exit is None:
                trade.slippage_exit = 0.0
                updated = True
            if updated:
                self.state_manager.add_trade(trade)
                self.notify_manager.send_notification(f"Trade Closed: {trade.type.capitalize()} {trade.symbol} closed at {trade.exit_price} Comment: {trade.comment}", "Close Trade (Broker Sync)")
