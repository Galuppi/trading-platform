import logging
import json

from app.base.base_engine import BaseEngine
from app.common.services.platform_time import PlatformTime
from app.common.config.paths import STATE_PATH, SUMMARY_PATH
from app.common.config.constants import MODE_BACKTEST, TRADE_STATUS_CLOSED

logger = logging.getLogger(__name__)

class EngineTester(BaseEngine):
    def __init__(self, connector, account, strategies, state_manager, simulation_timestamps, summary_writer, connector_config, backtester_config, dashboard_manager, risk_manager, news_manager = None, notify_manager =  None):
        super().__init__(connector, account, strategies, state_manager, connector_config, backtester_config, dashboard_manager, news_manager, risk_manager, summary_writer, notify_manager)
        self.connector = connector
        self.account=account
        self.simulation_timestamps = simulation_timestamps
        self.summary_writer = summary_writer
        self.connector_config = connector_config
        self.backtester_config = backtester_config
        self.news_manager = news_manager
        self.risk_manager = risk_manager
        self.notify_manager = notify_manager

        start_engine_timestamp = PlatformTime.timestamp()
        if self._update_and_check_profit_targets(start_engine_timestamp, 0) > 0:
            logger.info("Initial balances set.")

    def run(self):
        if STATE_PATH.exists():
            STATE_PATH.write_text(json.dumps({}))

        if SUMMARY_PATH.exists():
            SUMMARY_PATH.write_text(json.dumps({}))

        if self.simulation_timestamps:
            PlatformTime.set_backtest_timestamp(self.simulation_timestamps[0])

        self.initialize()

        last_balances_update = 0
        self.summary_writer.mark_wall_start()

        for i, current_timestamp in enumerate(self.simulation_timestamps, start=1):
            PlatformTime.set_backtest_timestamp(current_timestamp)

            last_balances_update = self._update_and_check_profit_targets(current_timestamp, last_balances_update)

            self._run_strategies()

            if i % 720 == 0:
                self.summary_writer.save()
                if self.backtester_config.backtest_terminal_output:
                    self.dashboard_manager.print_status_report(self.strategies, self.state_manager, MODE_BACKTEST, self.backtester_config, self.summary_writer)

        start_time = PlatformTime.from_timestamp(self.simulation_timestamps[0])
        end_time = PlatformTime.from_timestamp(self.simulation_timestamps[-1])
        initial_deposit = float(self.backtester_config.backtest_deposit)

        self.summary_writer.set_time_range(start_time, end_time)
        self.summary_writer.set_deposit_info(initial_deposit, self.summary_writer.get_total_profit())
        
        closed_tickets = self.state_manager.get_all_trades()
        closed_tickets = [t for t in closed_tickets if t.status == TRADE_STATUS_CLOSED and t.profit is not None]
        self.summary_writer.set_strategy_metrics(closed_tickets)

        self.summary_writer.mark_wall_end()
        self.summary_writer.save()

        self.shutdown()
        PlatformTime.clear_backtest_timestamp()


