from __future__ import annotations

from dataclasses import dataclass
from typing import Literal, Optional

ImpactLevel = Literal["Low", "Medium", "High", "Holiday"]

@dataclass(frozen=True, slots=True)
class FaireconomyEvent:
    date: str
    timestamp: Optional[int]
    time: str
    country: str
    impact: ImpactLevel
    title: str
    forecast: Optional[str]
    previous: Optional[str]