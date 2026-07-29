"""Loads the active strategy config profile from environment variables."""

import os


def load_strategy_config_profile() -> str:
    """Return the active strategy config profile (e.g. 'ftmo', 'ictrading', 'test').

    Determines which per-strategy config file is selected in discover_strategies():
    a profile of 'ftmo' selects 'ftmo_config.yaml' over the default 'config.yaml'.
    """
    return (os.getenv("STRATEGY_CONFIG", "") or "").lower()
