import importlib
import yaml
import logging
from pathlib import Path

from history.common.config.paths import DOWNLOADER_PATH
from history.common.models.model_downloader import DownloaderConfig, AssetConfig
from history.loaders.loader_history import get_history

logger = logging.getLogger(__name__)


def load_downloader_config(config_path: Path) -> DownloaderConfig:
    with open(config_path, "r", encoding="utf-8") as f:
        raw_config = yaml.safe_load(f)

    assets = [AssetConfig(**a) for a in raw_config.get("assets", [])]

    return DownloaderConfig(
        name=raw_config.get("name", config_path.parent.name),
        enabled=raw_config.get("enabled", True),
        assets=assets
    )


def discover_downloaders():
    for item in DOWNLOADER_PATH.iterdir():
        if item.is_dir() and not item.name.startswith("__"):
            downloader_file = item / "downloader.py"
            config_file = item / "config.yaml"
            if downloader_file.exists() and config_file.exists():
                yield item, downloader_file, config_file
            else:
                logger.warning(
                    f"Skipping '{item.name}': downloader.py or config.yaml not found"
                )


def downloader_registry_class(module_path: str, class_name: str):
    module = importlib.import_module(module_path)
    if not hasattr(module, class_name):
        raise ImportError(f"Class '{class_name}' not found in '{module_path}'")
    return getattr(module, class_name)


def downloader_registry(connector, history) -> list:
    downloaders = []

    for item, _, config_file in discover_downloaders():
        try:
            config = load_downloader_config(config_file)

            if not config.enabled:
                logger.info(f"Downloader '{config.name}' is disabled in config.")
                continue

            module_path = f"history.downloaders.{item.name}.downloader"
            class_name = (
                "".join(part.capitalize() for part in item.name.split("_")) + "Downloader"
            )

            downloader_class = downloader_registry_class(module_path, class_name)

            downloader = downloader_class(config=config)
            downloader.attach_services(connector=connector, history=history)

            downloaders.append(downloader)

        except Exception as e:
            logger.exception(f"Failed to load downloader from '{item.name}': {e}")

    return downloaders
