"""This module defines classes related to StateManager."""
import json
from dataclasses import asdict
from pathlib import Path
from typing import Dict, List, Optional, Union, Any
from app.common.services.platform_time import PlatformTime
from app.common.config.constants import DATETIME_FORMAT, TRADE_STATUS_OPEN, TRADE_STATUS_CLOSED, TRADE_DIRECTION_BUY, TRADE_DIRECTION_SELL
from app.common.models.model_trade import TradeRecord
from app.common.models.model_account import AccountSnapshot
from app.base.base_account import Account
from app.common.models.model_news import FaireconomyEvent

TradeLike = Union[TradeRecord, Dict[str, Any]]


class StateManager:
    def __init__(self, state_path: Path, account: Account, persist_enabled: bool = True) -> None:
        self.state_path = state_path
        self.persist_enabled = persist_enabled
        self.state: Dict[str, Dict[str, Any]] = {}
        self._cache: Dict[str, TradeRecord] = {}
        self.account = account
        self.state = self.load()

    def _key(self, trade_id: Any) -> str:
        return str(trade_id)

    def load(self) -> Dict[str, Dict[str, Any]]:
        if not self.persist_enabled:
            return {}
        if self.state_path.exists():
            with open(self.state_path, "r", encoding="utf-8") as f:
                data = json.load(f)
                if isinstance(data, dict):
                    self._cache = {}
                    for tid, tdata in data.items():
                        k = self._key(tid)
                        if k.startswith("_") or not isinstance(tdata, dict):
                            continue
                        try:
                            self._cache[k] = TradeRecord(**tdata)
                        except Exception:
                            pass
                    return {self._key(k): v for k, v in data.items()}
        return {}

    def _persist(self, state: Optional[Dict[str, Dict[str, Any]]] = None) -> None:
        if not self.persist_enabled:
            return
        if state is None:
            state = self.state
        with open(self.state_path, "w", encoding="utf-8") as f:
            json.dump(state, f, indent=4)

    def save(self) -> None:
        if not self.persist_enabled:
            return
        self._persist()

    def add_trade(self, trade: TradeRecord) -> None:
        if not isinstance(trade, TradeRecord):
            raise TypeError(f"add_trade expected TradeRecord, got {type(trade).__name__}")
        k = self._key(trade.id)
        self._cache[k] = trade
        self.state[k] = asdict(trade)
        self.save()

    def save_all_trades(self, trades: List[TradeLike]) -> None:
        meta = {k: v for k, v in self.state.items() if self._key(k).startswith("_")}
        new_trades: Dict[str, Dict[str, Any]] = {}
        new_cache: Dict[str, TradeRecord] = {}
        for item in trades:
            if isinstance(item, TradeRecord):
                k = self._key(item.id)
                new_trades[k] = asdict(item)
                new_cache[k] = item
            elif isinstance(item, dict) and "id" in item:
                k = self._key(item["id"])
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
        return [
            self._cache.get(k) or self._cache.setdefault(k, TradeRecord(**v))
            for k, v in self.state.items()
            if not str(k).startswith("_") and isinstance(v, dict)
        ]

    def count_trades_today(
        self,
        strategy: Optional[str] = None,
        symbol: Optional[str] = None,
        trade_type: Optional[str] = None,
    ) -> int:
        count = 0
        today = PlatformTime.now().date()
        for key, trade in self.state.items():
            if str(key).startswith("_"):
                continue
            if not isinstance(trade, dict):
                continue
            try:
                opened_dt = PlatformTime.strptime(trade.get("timestamp"), DATETIME_FORMAT)
            except Exception:
                continue
            if opened_dt.date() != today:
                continue
            if strategy is not None and trade.get("strategy") != strategy:
                continue
            if symbol is not None and trade.get("symbol") != symbol:
                continue
            if trade_type is not None and trade.get("type") != trade_type:
                continue
            count += 1
        return count

    def clean_old_closed_trades(self, max_age_hours: int = 24) -> None:
        cutoff = PlatformTime.now() - PlatformTime.timedelta(hours=max_age_hours)
        new_state: Dict[str, Dict[str, Any]] = {}
        for trade_id, trade in self.state.items():
            if str(trade_id).startswith("_"):
                new_state[trade_id] = trade
                continue
            if not isinstance(trade, dict):
                new_state[trade_id] = trade
                continue
            status = trade.get("status")
            exit_time_str = trade.get("exit_time")
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

    def clean_last_event(self) -> None:
        cleaned_state = {}
        for state_key, state_value in self.state.items():
            if state_key != "_last_event":
                cleaned_state[state_key] = state_value

        self.state = cleaned_state
        self._cache.pop("_last_event", None)
        self.save()

    def save_account_snapshot(self, equity: float, balance: float, target_reached: bool, break_even_reached: bool, weekly_profit_reached: bool) -> None:
        snapshot_data = self.state.get("_daily_profit")

        if not snapshot_data:
            begin_balance = round(balance, 2)
            begin_balance_week = round(balance, 2)
            profit = 0.0
            target_reached = False
            break_even_reached = False
            weekly_profit_reached = False
        else:
            begin_balance = snapshot_data["begin_balance"]
            begin_balance_week = snapshot_data["begin_balance_week"] or begin_balance
            profit = round(equity - begin_balance, 2)
            target_reached = bool(target_reached)
            break_even_reached = bool(break_even_reached)
            weekly_profit_reached = bool(weekly_profit_reached)
            
        snapshot = AccountSnapshot(
            timestamp=PlatformTime.datetime_str(),
            equity=float(equity),
            balance=float(balance),
            begin_balance=float(begin_balance),
            begin_balance_week=float(begin_balance_week),
            profit_floating=float(profit),
            profit_total_week=float(round(equity - begin_balance_week, 2)),
            target_reached=bool(target_reached),
            break_even_reached=bool(break_even_reached),
            weekly_profit_reached=bool(weekly_profit_reached),
        )

        self.state["_daily_profit"] = asdict(snapshot)
        self.save()

    def save_begin_balances(self) -> None:
        snapshot_data = self.state.get("_daily_profit")
        if not snapshot_data:
            return

        balance = snapshot_data["balance"]
        equity = snapshot_data["equity"]
        begin_balance_week = snapshot_data["begin_balance_week"]
        weekly_profit_reached = snapshot_data["weekly_profit_reached"]
        snapshot = AccountSnapshot(
            timestamp=PlatformTime.datetime_str(),
            begin_balance=float(round(balance, 2)),
            begin_balance_week=float(round(begin_balance_week, 2)),
            weekly_profit_reached=bool(weekly_profit_reached),
            equity=float(equity),
            balance=float(balance),
            profit_floating=0.0,
            profit_total_week=0.0,
            target_reached=False,
            break_even_reached=False,
        )
        self.state["_daily_profit"] = asdict(snapshot)
        self.save()

    def save_begin_balances_week(self) -> None:
        snapshot_data = self.state.get("_daily_profit")
        if not snapshot_data:
            return

        balance = snapshot_data["balance"]
        equity = snapshot_data["equity"]
        snapshot = AccountSnapshot(
            timestamp=PlatformTime.datetime_str(),
            begin_balance=float(round(balance, 2)),
            begin_balance_week=float(round(balance, 2)),
            equity=float(equity),
            balance=float(balance),
            profit_floating=0.0,
            profit_total_week=0.0,
            target_reached=False,
            break_even_reached=False,
            weekly_profit_reached=False,
        )
        self.state["_daily_profit"] = asdict(snapshot)
        self.save()

    def get_begin_balance(self) -> float:
        snapshot_data = self.state.get("_daily_profit")
        if snapshot_data and isinstance(snapshot_data, dict):
            return snapshot_data.get("begin_balance", 0.0)
        return 0.0

    def get_begin_balance_week(self) -> float:
        snapshot_data = self.state.get("_daily_profit")
        if snapshot_data and isinstance(snapshot_data, dict):
            return snapshot_data.get("begin_balance_week", 0.0)
        return 0.0
    
    def get_daily_profit(self) -> float:
        snapshot_data = self.state.get("_daily_profit")
        if snapshot_data and isinstance(snapshot_data, dict):
            return snapshot_data.get("profit", 0.0)
        return 0.0

    def get_target_reached(self) -> bool:
        snapshot_data: Optional[dict] = self.state.get("_daily_profit")      
        if snapshot_data is None:
            return False     
        return snapshot_data.get("target_reached", False)

    def get_weekly_profit_reached(self) -> bool:
        snapshot_data: Optional[dict] = self.state.get("_daily_profit")      
        if snapshot_data is None:
            return False     
        return snapshot_data.get("weekly_profit_reached", False)
       
    def get_break_even_reached(self) -> bool:
        snapshot_data: Optional[dict] = self.state.get("_daily_profit")      
        if snapshot_data is None:
            return False     
        return snapshot_data.get("break_even_reached", False)
    
    def get_account_snapshot(self) -> AccountSnapshot:
        snapshot_data: Optional[dict] = self.state.get("_daily_profit")     
        if snapshot_data is not None:
            begin_balance = round(snapshot_data["begin_balance"], 2)
            balance = round(snapshot_data["balance"], 2)
            equity = round(snapshot_data["equity"], 2)
            profit = round(snapshot_data["profit_floating"], 2)
            profit_total_week = round(snapshot_data["profit_total_week"], 2)
            target_reached = snapshot_data.get("target_reached", False)
            break_even_reached = snapshot_data.get("break_even_reached", False) 
        else:
            begin_balance = round(self.account.get_balance(), 2)
            balance = round(self.account.get_balance(), 2)
            equity = round(self.account.get_equity(), 2)
            profit = round(equity - balance, 2)
            target_reached = False
            break_even_reached = False
        
        return AccountSnapshot(
            timestamp=PlatformTime.datetime_str(),
            begin_balance=begin_balance,
            begin_balance_week=0,
            balance=balance,
            equity=equity,
            profit_floating=profit,
            profit_total_week=0.0,
            target_reached=target_reached,
            break_even_reached=break_even_reached,
        )

    def get_open_trades(
        self,
        symbol: Optional[str] = None,
        strategy: Optional[str] = None,
        date: Optional[PlatformTime.date] = None,
    ) -> List[TradeRecord]:
        trades = []
        for key, trade in self.state.items():
            if str(key).startswith("_") or not isinstance(trade, dict):
                continue
            if trade.get("status") != TRADE_STATUS_OPEN:
                continue
            if symbol is not None and trade.get("symbol") != symbol:
                continue
            if strategy is not None and trade.get("strategy") != strategy:
                continue
            if date:
                try:
                    opened = PlatformTime.strptime(trade.get("timestamp"), DATETIME_FORMAT)
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

    def save_server_time_offset(self, offset_hours: float) -> None:
        self.state["_server_time_offset"] = {"offset_hours": offset_hours}

    def get_server_time_offset(self) -> Optional[float]:
        offset_info = self.state.get("_server_time_offset")
        if isinstance(offset_info, dict):
            return offset_info.get("offset_hours")
        return None

    def save_server_last_tick(self, last_tick: int) -> None:
        self.state["_server_last_tick"] = {"last_tick": last_tick}

    def get_server_last_tick(self) -> Optional[int]:
        last_tick_info = self.state.get("_server_last_tick")
        if isinstance(last_tick_info, dict):
            return last_tick_info.get("last_tick")
        return None

    def get_last_trade(self, symbol: str) -> Optional[TradeRecord]:
        matching = [t for t in self.get_all_trades() if t.symbol == symbol]
        if not matching:
            return None
        
        latest = matching[0]
        for t in matching:
            if t.id > latest.id:
                latest = t
        return latest
    
    def get_last_closed_trade(self, symbol: str) -> Optional[TradeRecord]:
        closed_trades = [
            t for t in self.get_all_trades()
            if t.symbol == symbol and t.status.lower() == TRADE_STATUS_CLOSED
        ]

        if not closed_trades:
            return None

        latest = closed_trades[0]
        for t in closed_trades:
            if t.id > latest.id:
                latest = t

        return latest

    def save_last_event(
        self,
        event: FaireconomyEvent
    ) -> None:
        self.state["_last_event"] = {
            "event": {
                "date": event.date,
                "timestamp": event.timestamp,
                "time": event.time,
                "country": event.country,
                "impact": event.impact,
                "title": event.title,
                "forecast": event.forecast,
                "previous": event.previous,
            },
            "updated_at": PlatformTime.now().strftime(DATETIME_FORMAT),
        }
        self.save()

    def get_last_event(self) -> Optional[FaireconomyEvent]:
        data = self.state.get("_last_event")
        if not isinstance(data, dict):
            return None

        event_data = data.get("event")
        if not isinstance(event_data, dict):
            return None

        try:
            return FaireconomyEvent(
                date=event_data.get("date", ""),
                timestamp=event_data.get("timestamp"),
                time=event_data.get("time", ""),
                country=event_data.get("country", ""),
                impact=event_data.get("impact", "Low"),
                title=event_data.get("title", ""),
                forecast=event_data.get("forecast"),
                previous=event_data.get("previous"),
            )
        except Exception:
            return None

    def get_floating_profit(self, symbol: str | None = None) -> float:
        total_profit = 0.0
        for trade in self.get_all_trades():
            if trade.status != TRADE_STATUS_OPEN:
                continue

            if symbol is not None:
                if trade.symbol != symbol:
                    continue
                    
            if trade.profit is not None:
                total_profit += trade.profit
                
        return round(total_profit, 2)