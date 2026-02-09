import json
import os
import sys
from loguru import logger

patch = os.getcwd()
_LOGGER_CONFIGURED = False


def load_app_config(path="config.json"):
    with open(path, "r", encoding="utf-8") as file:
        return json.load(file)


def configure_logger(path="config.json"):
    global _LOGGER_CONFIGURED
    if _LOGGER_CONFIGURED:
        return

    config_data = load_app_config(path)
    logging_config = config_data.get("logging", {}) if isinstance(config_data, dict) else {}

    logs_dir = logging_config.get("dir")
    log_file = logging_config.get("file")
    log_level = logging_config.get("level")
    log_rotation = logging_config.get("rotation")
    log_retention = logging_config.get("retention")

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

    _LOGGER_CONFIGURED = True
