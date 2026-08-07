"""Database configuration."""

from dataclasses import dataclass


@dataclass
class DatabaseConfig:
    """Filename of the shared deals database, resolved against DATA_DIR."""
    filename: str
