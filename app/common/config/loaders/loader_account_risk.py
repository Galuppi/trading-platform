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
    enable_account_risk=risk_data["enabled"],
    if not enable_account_risk:
        return AccountRisk(
            account_risk_enabled=False,
            account_stop_loss=0.0,
            account_take_profit=0.0,
            account_break_even=0.0,
            account_profit_level=0.0,
            account_take_profit_week=0.0,
        )
    return AccountRisk(
        account_risk_enabled=True,
        account_stop_loss=risk_data["account_stop_loss"],
        account_take_profit=risk_data["account_take_profit"],
        account_break_even=risk_data["account_break_even"],
        account_profit_level=risk_data["account_profit_level"],
        account_take_profit_week=risk_data["account_take_profit_week"],
    )