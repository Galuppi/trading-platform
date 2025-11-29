from typing import Any

"""This module defines classes related to StateManager."""
import json
from dataclasses import asdict
from pathlib import Path
from typing import Dict, List, Optional, Union, Any
from app.common.system.platform_time import PlatformTime
from app.common.config.constants import DATETIME_FORMAT, TRADE_STATUS_OPEN, TRADE_STATUS_CLOSED
from app.common.models.model_trade import TradeRecord
from app.common.models.model_account import StateBalances, DailyProfitSnapshot
from app.base.base_account import Account
TradeLike = Union[TradeRecord, Dict[str, Any]]

class StateManager:

    def __init__(self, state_path: Path, account: Account, persist_enabled: bool=True) -> None:
        """Perform the defined operation."""
        self.state_path = state_path
        self.persist_enabled = persist_enabled
        self.state: Dict[str, Dict[str, Any]] = {}
        self._cache: Dict[str, TradeRecord] = {}
        self.account = account
        self.state = self.load()

    def _key(self, trade_id: Any) -> str:
        """Perform the defined operation."""
        return str(trade_id)

    def load(self) -> Dict[str, Dict[str, Any]]:
        """Perform the defined operation."""
        if not self.persist_enabled:
            return {}
        if self.state_path.exists():
            with open(self.state_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
                if isinstance(data, dict):
                    self._cache = {}
                    for tid, tdata in data.items():
                        k = self._key(tid)
                        if k.startswith('_') or not isinstance(tdata, dict):
                            continue
                        try:
                            self._cache[k] = TradeRecord(**tdata)
                        except Exception:
                            pass
                    return {self._key(k): v for k, v in data.items()}
        return {}

    def _persist(self, state: Optional[Dict[str, Dict[str, Any]]]=None) -> None:
        """Perform the defined operation."""
        if not self.persist_enabled:
            return
        if state is None:
            state = self.state
        with open(self.state_path, 'w', encoding='utf-8') as f:
            json.dump(state, f, indent=4)

    def save(self) -> None:
        """Perform the defined operation."""
        if not self.persist_enabled:
            return
        self._persist()

    def add_trade(self, trade: TradeRecord) -> None:
        """Perform the defined operation."""
        if not isinstance(trade, TradeRecord):
            raise TypeError(f'add_trade expected TradeRecord, got {type(trade).__name__}')
        k = self._key(trade.id)
        self._cache[k] = trade
        self.state[k] = asdict(trade)
        self.save()

    def save_all_trades(self, trades: List[TradeLike]) -> None:
        """Perform the defined operation."""
        meta = {k: v for k, v in self.state.items() if self._key(k).startswith('_')}
        new_trades: Dict[str, Dict[str, Any]] = {}
        new_cache: Dict[str, TradeRecord] = {}
        for item in trades:
            if isinstance(item, TradeRecord):
                k = self._key(item.id)
                new_trades[k] = asdict(item)
                new_cache[k] = item
            elif isinstance(item, dict) and 'id' in item:
                k = self._key(item['id'])
                new_trades[k] = item
                try:
                    new_cache[k] = TradeRecord(**item)
                except Exception:
                    pass
            else:
                raise TypeError("save_all_trades expects TradeRecord or dicts with an 'id' key")
        self.state = {**meta, **new_trades}
        self._cache = new_cache
        self.save()

    def get_trade_by_id(self, trade_id: str) -> Optional[TradeRecord]:
        """Perform the defined operation."""
        k = self._key(trade_id)
        cached = self._cache.get(k)
        if cached is not None:
            return cached
        trade = self.state.get(k)
        if isinstance(trade, dict):
            obj = TradeRecord(**trade)
            self._cache[k] = obj
            return obj
        return None

    def get_all_trades(self) -> List[TradeRecord]:
        """Perform the defined operation."""
        return [self._cache.get(k) or self._cache.setdefault(k, TradeRecord(**v)) for k, v in self.state.items() if not str(k).startswith('_') and isinstance(v, dict)]

    def get_execute_entrys(self, symbol: Optional[str]=None, strategy: Optional[str]=None, trade_type: Optional[str]=None) -> List[TradeRecord]:
        """Perform the defined operation."""
        result: List[TradeRecord] = []
        for key, trade in self.state.items():
            if str(key).startswith('_'):
                continue
            if not isinstance(trade, dict):
                continue
            if trade.get('status') != TRADE_STATUS_OPEN:
                continue
            if symbol is not None and trade.get('symbol') != symbol:
                continue
            if strategy is not None and trade.get('strategy') != strategy:
                continue
            if trade_type is not None and trade.get('type') != trade_type:
                continue
            obj = self._cache.get(key)
            if obj is None:
                try:
                    obj = TradeRecord(**trade)
                    self._cache[key] = obj
                except Exception:
                    continue
            result.append(obj)
        return result

    def count_trades_today(self, strategy: Optional[str]=None, symbol: Optional[str]=None, trade_type: Optional[str]=None) -> int:
        """Perform the defined operation."""
        count = 0
        today = PlatformTime.now().date()
        for key, trade in self.state.items():
            if str(key).startswith('_'):
                continue
            if not isinstance(trade, dict):
                continue
            try:
                opened_dt = PlatformTime.strptime(trade.get('timestamp'), DATETIME_FORMAT)
            except Exception:
                continue
            if opened_dt.date() != today:
                continue
            if strategy is not None and trade.get('strategy') != strategy:
                continue
            if symbol is not None and trade.get('symbol') != symbol:
                continue
            if trade_type is not None and trade.get('type') != trade_type:
                continue
            count += 1
        return count

    def can_open_trade(self, max_per_day: int, strategy: Optional[str]=None, symbol: Optional[str]=None, trade_type: Optional[str]=None) -> bool:
        """Perform the defined operation."""
        if max_per_day <= 0:
            return False
        return self.count_trades_today(strategy, symbol, trade_type) < max_per_day

    def clean_old_closed_trades(self, max_age_hours: int=24) -> None:
        """Perform the defined operation."""
        cutoff = PlatformTime.now() - PlatformTime.timedelta(hours=max_age_hours)
        new_state: Dict[str, Dict[str, Any]] = {}
        for trade_id, trade in self.state.items():
            if str(trade_id).startswith('_'):
                new_state[trade_id] = trade
                continue
            if not isinstance(trade, dict):
                new_state[trade_id] = trade
                continue
            status = trade.get('status')
            exit_time_str = trade.get('exit_time')
            if status != TRADE_STATUS_CLOSED:
                new_state[trade_id] = trade
                continue
            try:
                exit_time = PlatformTime.strptime(exit_time_str, DATETIME_FORMAT)
                if exit_time > cutoff:
                    new_state[trade_id] = trade
            except Exception:
                new_state[trade_id] = trade
        self.state = new_state
        removed = set(self._cache.keys()) - set(self.state.keys())
        for k in removed:
            self._cache.pop(k, None)
        self.save()

    def update_daily_profit(self, equity: float, balance: float) -> None:
        """Perform the defined operation."""
        snapshot = DailyProfitSnapshot(timestamp=PlatformTime.datetime_str(), equity=equity, balance=balance, profit=round(equity - balance, 2))
        self.state['_daily_profit'] = asdict(snapshot)
        self.save()

    def get_state_balances(self) -> StateBalances:
        """Perform the defined operation."""
        balance = round(self.account.get_balance(), 2)
        equity = round(self.account.get_equity(), 2)
        profit = round(equity - balance, 2)
        return StateBalances(balance=balance, equity=equity, profit=profit)

    def get_open_trades(self, symbol: Optional[str]=None, strategy: Optional[str]=None, date: Optional[PlatformTime.date]=None) -> List[TradeRecord]:
        """Perform the defined operation."""
        trades = []
        for key, trade in self.state.items():
            if str(key).startswith('_') or not isinstance(trade, dict):
                continue
            if trade.get('status') != TRADE_STATUS_OPEN:
                continue
            if symbol is not None and trade.get('symbol') != symbol:
                continue
            if strategy is not None and trade.get('strategy') != strategy:
                continue
            if date:
                try:
                    opened = PlatformTime.strptime(trade.get('timestamp'), DATETIME_FORMAT)
                    if opened.date() != date:
                        continue
                except Exception:
                    continue
            obj = self._cache.get(key)
            if obj is None:
                try:
                    obj = TradeRecord(**trade)
                    self._cache[key] = obj
                except Exception:
                    continue
            trades.append(obj)
        return trades

    def sync_status_with_broker(self, open_ticket_ids: List[str]) -> None:
        """Perform the defined operation."""
        open_ticket_ids_set = set(open_ticket_ids)
        for trade in self.get_all_trades():
            if trade.status == TRADE_STATUS_OPEN and str(trade.ticket) not in open_ticket_ids_set:
                trade.status = TRADE_STATUS_CLOSED
                trade.exit_time = PlatformTime.now().strftime(DATETIME_FORMAT)
                trade.comment = 'Closed externally'
                self.add_trade(trade)

    def sync_tickets_with_broker(self, closed_tickets: List[TradeRecord]) -> None:
        """Perform the defined operation."""
        if not closed_tickets:
            return
        closed_tickets_map = {str(t.ticket): t for t in closed_tickets}
        for trade in self.get_all_trades():
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
                self.add_trade(trade)

    def save_server_time_offset(self, offset_hours: float) -> None:
        """Perform the defined operation."""
        self.state['_server_time_offset'] = {'offset_hours': offset_hours}

    def get_server_time_offset(self) -> Optional[float]:
        """Perform the defined operation."""
        offset_info = self.state.get('_server_time_offset')
        if isinstance(offset_info, dict):
            return offset_info.get('offset_hours')
        return None

    def save_server_last_tick(self, last_tick: int) -> None:
        """Perform the defined operation."""
        self.state['_server_last_tick'] = {'last_tick': last_tick}

    def get_server_last_tick(self) -> Optional[int]:
        """Perform the defined operation."""
        last_tick_info = self.state.get('_server_last_tick')
        if isinstance(last_tick_info, dict):
            return last_tick_info.get('last_tick')
        return None

    def get_last_trade(self, symbol: str) -> Optional[TradeRecord]:
        """Perform the defined operation."""
        matching = [t for t in self.get_all_trades() if t.symbol == symbol]
        if not matching:
            return None
        latest = matching[0]
        for t in matching:
            if t.id > latest.id:
                latest = t
        return latest

    def get_last_closed_trade(self, symbol: str) -> Optional[TradeRecord]:
        """Perform the defined operation."""
        closed_trades = [t for t in self.get_all_trades() if t.symbol == symbol and t.status.lower() == TRADE_STATUS_CLOSED]
        if not closed_trades:
            return None
        latest = closed_trades[0]
        for t in closed_trades:
            if t.id > latest.id:
                latest = t
        return latest