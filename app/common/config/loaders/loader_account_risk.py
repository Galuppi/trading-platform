"""Loads per-account risk configuration (profit targets, stop loss, break-even) from YAML."""

import yaml
from pathlib import Path
from app.common.models.model_account import AccountRisk
from app.common.config.paths import ACCOUNT_RISK_PATH


def load_account_risk() -> AccountRisk:
    """Load global account risk settings."""
    path = Path(ACCOUNT_RISK_PATH)
    if not path.exists():
        raise FileNotFoundError("Account risk file not found.")

    with open(path, "r") as file:
        data = yaml.safe_load(file) or {}
    risk_data = data.get("risk", {})
    risk_enabled = risk_data["enabled"]
    if not risk_enabled:
        return AccountRisk(
            enabled=False,
            stop_loss=0.0,
            take_profit=0.0,
            break_even=0.0,
            profit_level=0.0,
            take_profit_week=0.0,
        )
    return AccountRisk(
        enabled=True,
        stop_loss=risk_data["stop_loss"],
        take_profit=risk_data["take_profit"],
        break_even=risk_data["break_even"],
        profit_level=risk_data["profit_level"],
        take_profit_week=risk_data["take_profit_week"],
    )
