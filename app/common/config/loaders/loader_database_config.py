"""Loads database configuration from environment variables."""

import logging
import os
from app.common.models.model_database import DatabaseConfig

logger = logging.getLogger(__name__)

DEFAULT_DATABASE_FILENAME = "deals.db"


def load_database_config() -> DatabaseConfig:
    """Reads DATABASE from .env, falling back to deals.db if unset."""
    filename = os.getenv("DATABASE")
    if not filename:
        logger.warning(f"DATABASE not set in environment. Using default '{DEFAULT_DATABASE_FILENAME}'.")
        filename = DEFAULT_DATABASE_FILENAME
    return DatabaseConfig(filename=filename)
