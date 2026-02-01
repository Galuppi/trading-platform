import json
import logging
import numpy
from pathlib import Path
from typing import Dict, List, Optional


from app.base.base_strategy import Strategy
from app.common.services.platform_time import PlatformTime
from app.common.models.model_strategy import StrategyConfig, AssetConfig
from app.common.models.model_trade import TradeRecord
from app.common.models.model_strategy import SentimentSignal
from app.common.config.constants import TRADE_DIRECTION_SELL, TRADE_DIRECTION_BUY

logger = logging.getLogger(__name__)


class SentimentStrategy(Strategy):
    def __init__(self, config: StrategyConfig) -> None:
        super().__init__(config=config)
        self.signals: Dict[str, SentimentSignal] = {}
        self.last_load: Optional[float] = None
        self.last_logged_event_ts: int = 0
        self.resume_trading: bool = False

    def initialize(self) -> None:
        for asset in self.assets:
            if not self.is_valid_symbol(asset.symbol):
                raise ValueError(f"Symbol '{asset.symbol}' not available or not visible in Market Watch")
        self._load_signals()

    def _get_signal(self, signal_symbol: str) -> Optional[SentimentSignal]:
        return self.signals.get(signal_symbol)

    def _is_buy_signal(self, signal: Optional[SentimentSignal], asset: AssetConfig) -> bool:
        if not signal or signal.sma24 is None or signal.sma4 is None:
            return False
        #return signal.sma24 > asset.signal_buy and signal.sma4 > asset.signal_buy
        return signal.sma24 >= asset.signal_buy and signal.sma4 >= asset.signal_buy and numpy.sign(signal.sma1) >= asset.signal_buy

    def _is_sell_signal(self, signal: Optional[SentimentSignal], asset: AssetConfig) -> bool:
        if not signal or signal.sma24 is None or signal.sma4 is None:
            return False
        #return (signal.sma24 < asset.signal_sell and signal.sma4 < asset.signal_sell) or signal.sma4 < 0 or signal.sma24 < 0
        return signal.sma24 <= asset.signal_sell and signal.sma4 <= asset.signal_sell and numpy.sign(signal.sma1) <= asset.signal_sell

    def is_entry_signal(self, asset: AssetConfig) -> Optional[str]:
        if self.state_manager.get_target_reached():
            if PlatformTime.local_now_utc().hour == 15:
                logger.info("Resetting begin balances and targets for new session")
                self.state_manager.save_begin_balances()
            return None
        
        if self.state_manager.get_weekly_profit_reached():
            return None
        
        event = self.news_manager.get_releasing_event(asset.symbol)
        if event and event.timestamp != self.last_logged_event_ts:
            self.state_manager.save_last_event(event)
            logger.info(f"Current news event: {event}")
            self.last_logged_event_ts = event.timestamp

        if self.news_manager.is_releasing_news(asset.symbol):
            self.resume_trading = False     
            return None
        else:
            if not self.resume_trading:
                logger.info(f"News event expired, resuming trading")
                self.resume_trading = True
      
        if self.has_reached_max_trades(asset):
            return None

        open_time = PlatformTime.compute_time_from_minutes(asset.open_min or 0)
        if PlatformTime.now().time() < open_time:
            return None
        
        last_trade = self.state_manager.get_last_trade(asset.symbol)
        if last_trade is not None:
            last_trade_time = PlatformTime.parse_datetime_str(last_trade.timestamp)        
            time_since_last_trade = PlatformTime.now() - last_trade_time              
            if time_since_last_trade < PlatformTime.timedelta(minutes=(asset.trade_cooldown_minutes or 0)):
                return None

        if self.state_manager.get_floating_profit(asset.symbol) < -10.0:
            logger.info(f"Skipping new trade for {asset.symbol} due to insufficient profit on existing position")
            return None

        last_closed_trade = self.state_manager.get_last_closed_trade(asset.symbol)
        if last_closed_trade is not None:
            if last_closed_trade.exit_time is None:
                logger.warning( f"Last closed trade ({last_closed_trade.id}) has no exit_time — skipping cooldown check")
            else:
                if last_closed_trade.profit < 0:
                    exit_time = PlatformTime.parse_datetime_str(last_closed_trade.exit_time)
                    time_since_close = PlatformTime.now() - exit_time
                    if time_since_close < PlatformTime.timedelta(minutes=120):
                        return None
                    
        self._load_signals()
        signal = self._get_signal(asset.signal_symbol)

        if self._is_buy_signal(signal, asset):
            return TRADE_DIRECTION_BUY
        if self._is_sell_signal(signal, asset):
            return TRADE_DIRECTION_SELL
        return None

    def is_exit_signal(self, trade: TradeRecord) -> bool:
        if self.state_manager.get_target_reached():
            return True

        if self.state_manager.get_weekly_profit_reached():
            return True
        
        if trade.strategy != self.strategy_name:
            return False
                
        for asset in self.assets:
            if asset.symbol == trade.symbol:
                return PlatformTime.minutes_since_midnight() >= (asset.close_min or 0) or self.news_manager.is_releasing_news(asset.symbol)
        return False

    def _load_signals(self):
        try:
            signal_feed_path = Path(self.config.signal_feed)
            if not signal_feed_path.exists():
                self.signals = {}
                return

            with open(signal_feed_path, "r", encoding="utf-8") as f:
                raw_data = f.read()
                if not raw_data.strip():
                    self.signals = {}
                    return

                data = json.loads(raw_data)
                file_timestamp_str = data.get("timestamp")
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

            file_modified_time = signal_feed_path.stat().st_mtime
            if self.last_load and file_modified_time == self.last_load:
                return

            with open(signal_feed_path, "r", encoding="utf-8") as json_file:
                signal_payload = json.load(json_file)

            parsed_signals = []
            for signal_entry in signal_payload.get("signals", []):
                try:
                    sentiment_signal = SentimentSignal(
                        symbol=signal_entry.get("symbol"),
                        category=signal_entry.get("category"),
                        sma24=signal_entry.get("sma24"),
                        sma4=signal_entry.get("sma4"),
                        sma1=signal_entry.get("sma1"),
                        price=signal_entry.get("price"),
                        countsma24=signal_entry.get("countsma24"),
                        countsma4=signal_entry.get("countsma4"),
                        countsma1=signal_entry.get("countsma1"),
                        timestamp=signal_entry.get("timestamp"),
                    )
                    parsed_signals.append(sentiment_signal)
                except Exception as error:
                    logger.warning(f"Invalid signal entry skipped: {error}")

            self.signals = {signal.symbol: signal for signal in parsed_signals if signal.symbol}
            self.last_load = file_modified_time
            logger.info(f"Loaded {len(self.signals)} fresh signals from {file_timestamp_str}")

        except Exception as error:
            logger.error(f"Failed to load signal file: {error}")
            self.signals = {}
            self.last_load = None