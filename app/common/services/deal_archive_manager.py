"""Archives closed trades into a local SQLite database for downstream reporting (e.g. Metabase)."""

import logging
import sqlite3
from pathlib import Path
from typing import List

from app.common.config.constants import TRADE_STATUS_CLOSED
from app.common.models.model_trade import TradeRecord

logger = logging.getLogger(__name__)

CREATE_TABLE_SQL = """
CREATE TABLE IF NOT EXISTS deals (
    id TEXT NOT NULL,
    platform TEXT NOT NULL,
    account_id TEXT NOT NULL,
    symbol TEXT,
    lot_size REAL,
    type TEXT,
    ticket TEXT,
    status TEXT,
    timestamp TEXT,
    strategy TEXT,
    strategy_id INTEGER,
    entry_price REAL,
    exit_price REAL,
    exit_time TEXT,
    stop_loss REAL,
    stop_loss_points INTEGER,
    take_profit REAL,
    commission REAL,
    comment TEXT,
    profit REAL,
    slippage_entry REAL,
    slippage_exit REAL,
    PRIMARY KEY (platform, account_id, id)
)
"""

INSERT_DEAL_SQL = """
INSERT OR IGNORE INTO deals (
    id, platform, account_id, symbol, lot_size, type, ticket, status,
    timestamp, strategy, strategy_id, entry_price, exit_price, exit_time,
    stop_loss, stop_loss_points, take_profit, commission, comment,
    profit, slippage_entry, slippage_exit
) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
"""

# seconds SQLite waits for a lock to clear before raising "database is locked" —
# relevant now that multiple instances (MT5, cTrader) can write to the same shared file
SQLITE_BUSY_TIMEOUT_SECONDS = 30


class DealArchiveManager:
    """Archives closed trades into a local SQLite database for downstream reporting (e.g. Metabase)."""

    def __init__(self, db_path: Path, platform: str, account_id: str) -> None:
        self.db_path = db_path
        self.platform = platform
        self.account_id = account_id
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_schema()

    def _init_schema(self) -> None:
        with sqlite3.connect(self.db_path, timeout=SQLITE_BUSY_TIMEOUT_SECONDS) as conn:
            conn.execute(CREATE_TABLE_SQL)

    def archive_closed_trades(self, trades: List[TradeRecord]) -> int:
        """Insert any closed trades not already archived. Returns the number of newly archived rows."""
        closed_trades = [trade for trade in trades if trade.status == TRADE_STATUS_CLOSED]
        if not closed_trades:
            return 0

        inserted = 0
        with sqlite3.connect(self.db_path, timeout=SQLITE_BUSY_TIMEOUT_SECONDS) as conn:
            for trade in closed_trades:
                cursor = conn.execute(
                    INSERT_DEAL_SQL,
                    (
                        trade.id,
                        self.platform,
                        self.account_id,
                        trade.symbol,
                        trade.lot_size,
                        trade.type,
                        trade.ticket,
                        trade.status,
                        trade.timestamp,
                        trade.strategy,
                        trade.strategy_id,
                        trade.entry_price,
                        trade.exit_price,
                        trade.exit_time,
                        trade.stop_loss,
                        trade.stop_loss_points,
                        trade.take_profit,
                        trade.commission,
                        trade.comment,
                        trade.profit,
                        trade.slippage_entry,
                        trade.slippage_exit,
                    ),
                )
                inserted += cursor.rowcount

        if inserted:
            logger.info(f"Archived {inserted} new closed trade(s) to {self.db_path}")
        return inserted
