from abc import ABC, abstractmethod
import pandas as pd
from datetime import datetime

class History(ABC):
    @abstractmethod
    def get_historical_data(
        self,
        symbol: str,
        timeframe: str,
        start_date: datetime = None,
        end_date: datetime = None
    ) -> pd.DataFrame:
        """Retrieve historical price data for a symbol within a date range using platform time."""
        pass
