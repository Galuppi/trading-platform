"""Loads logging configuration from environment variables."""

import os


def load_log_level() -> str:
    return (os.getenv("LOG_LEVEL", "INFO") or "INFO").upper()
