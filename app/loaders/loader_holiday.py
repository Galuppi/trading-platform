from typing import Any

import yaml
from pathlib import Path
from app.common.config.paths import HOLIDAY_PATH

def load_holiday_calendar(region: str) -> list[str]:
    """Perform the defined operation."""
    path = Path(str(HOLIDAY_PATH).format(region.lower()))
    if not path.exists():
        raise FileNotFoundError(f'Holiday file not found for region: {region}')
    with open(path, 'r') as file:
        data = yaml.safe_load(file)
    return data.get('holidays', [])