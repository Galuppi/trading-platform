from history.connectors.mt5.mt5_history import Mt5History
from history.connectors.mt5.mt5_calculator import Mt5HistoryCalculator
from history.connectors.ctrader.ctrader_history import CTraderHistory
from history.connectors.ctrader.ctrader_calculator import CTraderHistoryCalculator


def get_history(platform: str):
    if platform == "mt5":
        calculator = Mt5HistoryCalculator()
        return Mt5History(calculator)
    elif platform == "ctrader":
        calculator = CTraderHistoryCalculator()
        return CTraderHistory(calculator)
    else:
        raise ValueError(f"Unsupported platform for history: {platform}")
