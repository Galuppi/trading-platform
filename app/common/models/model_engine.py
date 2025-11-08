'''"""This module defines classes related to TestPeriod, Timestamps."""'''
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
