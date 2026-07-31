"""SMA crossover strategy driven by live quote/price data."""

import json
import logging
import numpy
from pathlib import Path
from typing import Dict, List, Optional


from app.base.base_strategy import Strategy
from app.common.services.platform_time import PlatformTime
from app.common.models.model_strategy import StrategyConfig, AssetConfig
from app.common.models.model_trade import TradeRecord
from app.common.models.model_strategy import Signal
from app.common.config.constants import TRADE_DIRECTION_SELL, TRADE_DIRECTION_BUY, TRADE_STATUS_OPEN

logger = logging.getLogger(__name__)

ACT_ON_NEWS_RELEASES = False
TRADE_CATEGORY = "quotes" 


class QuotesCrossStrategy(Strategy):
    """SMA crossover strategy driven by live quote/price data."""
    def __init__(self, config: StrategyConfig) -> None:
        super().__init__(config=config)
        self.signals: Dict[str, Signal] = {}
        self.last_load: Optional[float] = None
        self.resume_trading: bool = False

    def initialize(self) -> None:
        for asset in self.assets:
            if not self.is_valid_symbol(asset.symbol):
                raise ValueError(f"Symbol '{asset.symbol}' not available or not visible in Market Watch")
        self._load_signals()

    def _get_signal(self, signal_symbol: str) -> Optional[Signal]:
        return self.signals.get(signal_symbol)

    def _passes_atr_gate(self, spread: float, atr24: Optional[float]) -> bool:
        """Veto a crossover if the SMA spread is still within typical recent
        volatility for this symbol (i.e. likely zigzag noise rather than a
        real trend shift). Entries only -- callers on the exit path must
        pass apply_gate=False, since an exit should fire on any reversal
        regardless of its size."""
        if not self.config.atr_gate_enabled:
            return True
        if atr24 is None or atr24 == 0:
            logger.warning("ATR gate enabled but atr24 missing/zero for signal — blocking entry")
            return False
        ratio = abs(spread) / atr24
        if ratio <= self.config.atr_gate_multiplier:
            logger.debug(f"ATR gate blocked entry: ratio={ratio:.2f} <= k={self.config.atr_gate_multiplier:.2f}")
            return False
        return True

    def _is_buy_signal(self, signal: Optional[Signal], asset: AssetConfig, apply_gate: bool = True) -> bool:
        if not signal or signal.sma24 is None or signal.sma4 is None:
            return False
        if self.is_vix_paused():
            return False
        if signal.sma4 <= signal.sma24:
            return False
        if apply_gate and not self._passes_atr_gate(signal.sma4 - signal.sma24, signal.atr24):
            return False
        return True

    def _is_sell_signal(self, signal: Optional[Signal], asset: AssetConfig, apply_gate: bool = True) -> bool:
        if not signal or signal.sma24 is None or signal.sma4 is None:
            return False
        if self.is_vix_paused():
            return False
        if signal.sma4 >= signal.sma24:
            return False
        if apply_gate and not self._passes_atr_gate(signal.sma4 - signal.sma24, signal.atr24):
            return False
        return True

    def is_entry_signal(self, asset: AssetConfig) -> Optional[str]:
        if not PlatformTime.is_within_weekday_range(asset.open_day or 1, asset.close_day or 5):
            return None

        if self.state_manager.get_target_reached():
            return None

        if self.state_manager.get_weekly_profit_reached():
            return None

        if ACT_ON_NEWS_RELEASES:
            if self.news_manager.is_releasing_news(asset.symbol):
                self.resume_trading = False
                return None
            else:
                if not self.resume_trading:
                    logger.info("News event expired, resuming trading")
                    self.resume_trading = True

        open_time = PlatformTime.compute_time_from_minutes(asset.open_min or 0)
        if PlatformTime.now().time() < open_time:
            return None

        close_time = PlatformTime.compute_time_from_minutes(asset.close_min or 0)
        if PlatformTime.now().time() > close_time:
            return None

        last_closed_trade = self.state_manager.get_last_closed_trade(asset.symbol, strategy=self.strategy_name)
        if last_closed_trade is not None:
            if last_closed_trade.exit_time is None:
                logger.warning(f"Last closed trade ({last_closed_trade.id}) has no exit_time — skipping cooldown check")
            else:
                if last_closed_trade.comment == "Closed externally":  # fix this.
                    exit_time = PlatformTime.parse_datetime_str(last_closed_trade.exit_time)
                    time_since_close = PlatformTime.now() - exit_time
                    if time_since_close < PlatformTime.timedelta(minutes=360):
                        return None

        self._load_signals()
        signal = self._get_signal(asset.signal_symbol)

        if self.is_vix_paused():
            return None

        first_open_trade = self.state_manager.get_first_open_trade(asset.symbol, strategy=self.strategy_name)
        first_open_trade_direction = first_open_trade.type if first_open_trade else None
        if self._is_buy_signal(signal, asset):
            if first_open_trade_direction != TRADE_DIRECTION_BUY:
                return TRADE_DIRECTION_BUY
        if self._is_sell_signal(signal, asset):
            if first_open_trade_direction != TRADE_DIRECTION_SELL:
                return TRADE_DIRECTION_SELL
        return None

    def is_exit_signal(self, trade: TradeRecord, asset_config: AssetConfig) -> bool:
        if trade.strategy != self.strategy_name:
            return False

        current_time = PlatformTime.now().time()
        open_time = PlatformTime.compute_time_from_minutes(asset_config.open_min or 0)
        if current_time < open_time:
            return False

        close_time = PlatformTime.compute_time_from_minutes(asset_config.close_min or 0)
        if current_time > close_time:
            if PlatformTime.is_matching_weekday(asset_config.close_day or 5):
                return True
            return False

        if self.state_manager.get_target_reached():
            return True

        if self.state_manager.get_weekly_profit_reached():
            return True

        is_releasing_news = self.news_manager.is_releasing_news(trade.symbol)
        if is_releasing_news and ACT_ON_NEWS_RELEASES:
            return True

        signal_symbol = asset_config.signal_symbol
        signal = self._get_signal(signal_symbol)

        first_open_trade = self.state_manager.get_first_open_trade(trade.symbol, strategy=self.strategy_name)
        first_open_trade_direction = first_open_trade.type if first_open_trade else None
        if self._is_buy_signal(signal, trade, apply_gate=False):
            if first_open_trade_direction == TRADE_DIRECTION_SELL:
                return True
        if self._is_sell_signal(signal, trade, apply_gate=False):
            if first_open_trade_direction == TRADE_DIRECTION_BUY:
                return True
        return False

    def _load_signals(self) -> None:
        try:
            signal_feed_path = Path(self.config.signal_feed)
            if not signal_feed_path.exists():
                self.signals = {}
                return

            file_modified_time = signal_feed_path.stat().st_mtime
            if self.last_load and file_modified_time == self.last_load:
                return

            with open(signal_feed_path, "r", encoding="utf-8") as f:
                raw_data = f.read()
                if not raw_data.strip():
                    self.signals = {}
                    return
                signal_payload = json.loads(raw_data)

            file_timestamp_str = signal_payload.get("timestamp")
            if not file_timestamp_str:
                logger.warning("Signal file missing 'timestamp' field")
                self.signals = {}
                return

            try:
                file_time = PlatformTime.strptime(file_timestamp_str, "%Y-%m-%d %H:%M").replace(tzinfo=None)
                now_local = PlatformTime.local_now()
                age = now_local - file_time

                if age > PlatformTime.timedelta(hours=1):
                    logger.info(f"Signal file too old: {file_timestamp_str} ({age}), skipping load")
                    self.signals = {}
                    self.last_load = None
                    return
            except Exception as e:
                logger.warning(f"Failed to parse timestamp '{file_timestamp_str}': {e}, skipping file")
                self.signals = {}
                return

            parsed_signals = []
            for signal_entry in signal_payload.get(TRADE_CATEGORY, []):
                try:
                    signal_obj = Signal(
                        symbol=signal_entry.get("symbol"),
                        category=signal_entry.get("category"),
                        sma24=signal_entry.get("sma24"),
                        sma4=signal_entry.get("sma4"),
                        sma1=signal_entry.get("sma1"),
                        countsma24=signal_entry.get("countsma24"),
                        countsma4=signal_entry.get("countsma4"),
                        countsma1=signal_entry.get("countsma1"),
                        atr24=signal_entry.get("atr24"),
                        timestamp=signal_entry.get("timestamp"),
                    )
                    parsed_signals.append(signal_obj)
                except Exception as error:
                    logger.warning(f"Invalid signal entry skipped: {error}")

            self.signals = {signal.symbol: signal for signal in parsed_signals if signal.symbol}
            self.last_load = file_modified_time
            logger.info(
                f"Loaded {len(self.signals)} fresh '{TRADE_CATEGORY}' signals from {file_timestamp_str}"
            )

        except Exception as error:
            logger.error(f"Failed to load signal file: {error}")
            self.signals = {}
            self.last_load = None