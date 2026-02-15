import logging

from app.common.services.platform_time import PlatformTime
from app.common.config.constants import MODE_LIVE
from app.base.base_engine import BaseEngine

logger = logging.getLogger(__name__)

class Engine(BaseEngine):
    def run(self):
        self.initialize()
        PlatformTime.sleep(1)
        self.dashboard_manager.print_status_report(self.strategies, self.state_manager, MODE_LIVE, log_to_terminal=True)
        last_balances_update = 0
        last_news_refresh_update = 0

        start_engine_timestamp =PlatformTime.timestamp()
        if self._update_and_check_profit_targets(start_engine_timestamp, 0) > 0:
            logger.info("Initial balances set.")

        try:
            while True:
                if not self.connector.connection_check():
                    logger.warning("Connection lost. Attempting to reconnect...")
                    if self.connector.connect():
                        logger.info("Reconnected successfully.")
                    else:
                        logger.error("Reconnection failed. Retrying in 30 seconds...")
                        PlatformTime.sleep(30)
                        continue
                
                current_timestamp = PlatformTime.timestamp()

                last_tick_timestamp = self.state_manager.get_server_last_tick()
                current_tick_timestamp = self.account.get_server_tick_timestanp()

                server_time_offset = None   
                if last_tick_timestamp is not None and last_tick_timestamp != current_tick_timestamp:
                    server_time_offset = self.account.get_server_offset_hours()

                if server_time_offset is not None:
                    PlatformTime.set_offset(server_time_offset)
                    self.state_manager.save_server_time_offset(server_time_offset)
                
                if server_time_offset is None and self.state_manager.get_server_time_offset() is not None:
                    persisted_offset = self.state_manager.get_server_time_offset()
                    PlatformTime.set_offset(persisted_offset)

                open_ticket_ids = self.account.get_open_tickets()
                self.sync_manager.sync_status_with_broker(open_ticket_ids)
                closed_tickets = self.account.get_closed_tickets()
                self.sync_manager.sync_tickets_with_broker(closed_tickets)
                self.state_manager.save_server_last_tick(current_tick_timestamp)
                last_news_refresh_update = self._periodic_news_calendar_refresh(current_timestamp, last_news_refresh_update)
                last_balances_update = self._update_and_check_profit_targets(current_timestamp, last_balances_update)                                             
                self.dashboard_manager.print_status_report(self.strategies, self.state_manager, MODE_LIVE, log_to_terminal=True)

                self._run_strategies()
              
                PlatformTime.sleep(30)
        except KeyboardInterrupt:
            self.shutdown()
