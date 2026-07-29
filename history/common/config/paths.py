import os
from pathlib import Path

BASE_PATH = Path(__file__).resolve().parents[3]

DATA_PATH = BASE_PATH / "historical-data"
DOWNLOADER_PATH = BASE_PATH / "history" / "downloaders"
LOG_PATH = BASE_PATH / "history" / "runtime" / "logs"