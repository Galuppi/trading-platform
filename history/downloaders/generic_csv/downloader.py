from typing import Any

import logging
import pandas as pd
from pathlib import Path
from datetime import datetime
from history.base.base_downloader import Download
from history.common.models.model_downloader import DownloaderConfig
from history.common.config.paths import DATA_PATH
from history.common.config.constants import DATETIME_FORMAT
from history.base.base_history import History
logger = logging.getLogger(__name__)

class GenericCsvDownloader(Download):

    def __init__(self, config: DownloaderConfig) -> Any:
        """Perform the defined operation."""
        self.config = config
        self.connector = None
        self.history: History = None

    def attach_services(self, connector: Any, history: History) -> Any:
        """Perform the defined operation."""
        self.connector = connector
        self.history = history

    def initialize(self) -> Any:
        """Perform the defined operation."""
        logger.info(f'Initialized downloader: {self.config.name}')

    def run(self, config: Any=None) -> Any:
        """Perform the defined operation."""
        logger.info(f'Starting downloads for {self.config.name}')
        for asset in self.config.assets:
            output_dir = DATA_PATH / asset.symbol
            output_dir.mkdir(parents=True, exist_ok=True)
            try:
                start_date = datetime.strptime(asset.date_from, '%d-%m-%Y')
                end_date = datetime.strptime(asset.date_to, '%d-%m-%Y')
                df = self.history.get_historical_data(symbol=asset.symbol, timeframe=asset.timeframe, start_date=start_date, end_date=end_date)
                if df.empty:
                    logger.warning(f'No data for {asset.symbol} between {asset.date_from} and {asset.date_to}')
                    continue
                df['time'] = pd.to_datetime(df['time'])
                df['year'] = df['time'].dt.year
                for year, year_df in df.groupby('year'):
                    filename = f'{asset.symbol}_{year}_{asset.timeframe.upper()}.csv'
                    output_file = output_dir / filename
                    if output_file.exists():
                        logger.info(f'Skipping {filename} — already exists.')
                        continue
                    year_df.drop(columns='year', inplace=True)
                    year_df.to_csv(output_file, index=False, date_format=DATETIME_FORMAT)
                    logger.info(f'Wrote {len(year_df)} rows to {output_file}')
            except Exception as error:
                logger.error(f'Failed to download {asset.symbol}: {error}')