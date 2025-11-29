from typing import Any

from dataclasses import dataclass
from datetime import datetime

@dataclass
class TestPeriod:
    date_from: datetime
    date_to: datetime
    timeframe: str

@dataclass
class Timestamps:
    values: list[int]