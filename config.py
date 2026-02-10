import json
import os
import sys
from typing import Any

from loguru import logger

patch = os.getcwd()
_LOGGER_STATE = {"configured": False}


def load_app_config(path: str = "config.json") -> dict[str, Any]:
    with open(path, "r", encoding="utf-8") as file:
        data = json.load(file)
    return data if isinstance(data, dict) else {}


def configure_logger(path: str = "config.json") -> None:
    if _LOGGER_STATE["configured"]:
        return

    config_data = load_app_config(path)
    logging_config_raw = config_data.get("logging", {})
    logging_config = logging_config_raw if isinstance(logging_config_raw, dict) else {}

    logs_dir = str(logging_config.get("dir") or "logs")
    log_file = str(logging_config.get("file") or "app.log")
    log_level = str(logging_config.get("level") or "INFO")
    log_rotation = str(logging_config.get("rotation") or "10 MB")
    log_retention = str(logging_config.get("retention") or "7 days")

    os.makedirs(logs_dir, exist_ok=True)
    log_path = os.path.join(logs_dir, log_file)

    logger.remove()
    logger.add(
        sys.stderr,
        level=log_level,
        enqueue=True,
    )
    logger.add(
        log_path,
        level=log_level,
        rotation=log_rotation,
        retention=log_retention,
        encoding="utf-8",
        enqueue=True,
    )

    _LOGGER_STATE["configured"] = True
