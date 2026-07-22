"""Data model for a single VIX reading."""

from dataclasses import dataclass
from datetime import datetime


@dataclass
class VixReading:
    """A single VIX value captured from the configured feed."""
    value: float
    read_at: datetime
