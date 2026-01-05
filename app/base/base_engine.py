from abc import ABC, abstractmethod
import logging

from app.common.config.constants import TRADE_STATUS_CLOSED, MODE_LIVE, TRADE_STATUS_OPEN
from app.common.config.paths import LOG_PATH
from app.common.system.platform_time import PlatformTime
from app.common.system.logger import setup_logger

logger = logging.getLogger(__name__)

class BaseEngine(ABC):

    def __init__(self, connector, account, strategies, state_manager, connector_config, backtester_config, dashboard_manager=None, news_manager=None, risk_manager=None):
        """Initialize the engine with a list of strategies and a state manager."""
        self.connector = connector
        self.account = account
        self.strategies = strategies
        self.state_manager = state_manager
        self.connector_config = connector_config
        self.backtester_config = backtester_config
        self.today = PlatformTime.now().day
        self.dashboard_manager = dashboard_manager
        self.news_manager = news_manager
        self.risk_manager = risk_manager

    def initialize(self):
        """Call the initialize method on all strategies."""
        logger.info("Initializing strategies...")
        for strategy in self.strategies:
            strategy.initialize()
        logger.info("All strategies initialized.")

    def shutdown(self):
        """Finalize all strategies and perform shutdown procedures."""
        for strategy in self.strategies:
            strategy.finalize()
        logger.info("Trading system shutdown complete.")
    
    def _run_strategies(self):
        if self.today != PlatformTime.now().day:
            self.state_manager.clean_last_event()
            self.state_manager.save_begin_balances()
            self.risk_manager.initialize()
            setup_logger(LOG_PATH, self.connector_config.mode)       

        for strategy in self.strategies:
            if strategy.is_holiday() or not strategy.is_market_open():
                continue

            strategy.set_range()

            for asset in strategy.assets:
                try:
                    direction = strategy.is_entry_signal(asset)
                except Exception as e:
                    logger.warning(f"Skipping asset {asset.symbol} due to signal error: {e}")
                    continue

                if direction:
                    try:
                        order = strategy.prepare_order(asset, direction)
                    except Exception as e:
                        continue

                    try:
                        if strategy.is_entry_allowed(asset, order):
                            strategy.execute_entry(order)
                    except Exception as error:
                        logger.warning(f"Failed to open trade for {asset.symbol}: {error}")

                try:
                    for trade in self.state_manager.get_execute_entrys(
                        symbol=asset.symbol,
                        strategy=strategy.strategy_name
                    ):                        
                        if strategy.is_exit_signal(trade) and strategy.is_exit_allowed(trade):
                            try:
                                strategy.execute_exit(trade, stopped=False)
                            except Exception as error:
                                logger.warning(f"Failed to close trade {trade.id}: {error}")

                        has_sl = trade.stop_loss is not None and trade.stop_loss > 0
                        has_tp = trade.take_profit is not None and trade.take_profit > 0
                        if has_sl or has_tp:
                            if strategy.is_sl_tp_hit(trade) and strategy.is_exit_allowed(trade):
                                try:
                                    strategy.execute_exit(trade, stopped=True)
                                except Exception as error:
                                    logger.warning(f"Failed to close trade {trade.id}: {error}")

                        if trade.status == TRADE_STATUS_OPEN:
                            try:
                                strategy.manage_entry(trade)
                            except Exception as error:
                                logger.warning(f"Failed to manage trade {trade.id}: {error}")    
                                           
                    if self.connector_config.mode == MODE_LIVE:
                        self.state_manager.clean_old_closed_trades()
                except Exception as e:
                    logger.warning(f"Error checking exits for {asset.symbol}: {e}")

        self.today = PlatformTime.now().day

    def _update_daily_balances_if_due(self, timestamp, last_update_timestamp):
        """Update daily profit if the interval has elapsed since last update."""
        if timestamp - last_update_timestamp < 60:
            return last_update_timestamp

        try:
            risk_manager = self.risk_manager
            account_take_profit = risk_manager.get_account_take_profit() if risk_manager else 0
            account_stop_loss = risk_manager.get_account_stop_loss() if risk_manager else 0
            account_break_even = risk_manager.get_account_break_even() if risk_manager else 0
            account_risk_enabled = risk_manager.get_account_risk_enabled() if risk_manager else False
            begin_balance = self.state_manager.get_begin_balance()
            equity = self.account.get_equity()
            balance = self.account.get_balance()

            break_even_reached = self.state_manager.get_break_even_reached()
            account_profit_level = self.risk_manager.get_account_profit_level() 
            if break_even_reached is False and begin_balance > 0:
                break_even_reached = equity - begin_balance >= account_break_even if account_risk_enabled else False  
                if break_even_reached:
                    self.risk_manager.update_account_stop_loss(account_profit_level) 
                    logger.info("Break-even level reached. Adjusting account stop loss.") 

            take_profit_reached = equity - begin_balance >= account_take_profit if account_risk_enabled else False
            stop_loss_reached = equity - begin_balance  <= account_stop_loss if account_risk_enabled else False          
            target_reached = take_profit_reached or stop_loss_reached

            self.state_manager.save_daily_balances(equity, balance, target_reached, break_even_reached)
        except Exception as error:
            logger.warning(f"Failed to update profit: {error}")

        return timestamp

    def _refresh_calendar_if_due(self, timestamp, last_news_refresh_update):
        if timestamp - last_news_refresh_update >= 86400:
            try:
                self.news_manager.refresh()
            except Exception as error:
                logger.warning(f"Failed to refresh calendar: {error}")
            return timestamp
        return last_news_refresh_update

    @abstractmethod
    def run(self):
        """Entry point for the engine execution loop."""
        pass
