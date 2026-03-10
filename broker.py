import os
import socket
from urllib.parse import urlparse

import dramatiq
from dramatiq.brokers.redis import RedisBroker
from dramatiq.brokers.stub import StubBroker
from loguru import logger

from config import configure_logger, load_app_config

configure_logger()
config_data = load_app_config()

redis_url = os.getenv("REDIS_URL", config_data["redis_url"])
broker_kind = str(os.getenv("DRAMATIQ_BROKER", "redis")).strip().lower()


def _can_resolve_redis_host(url: str) -> bool:
    try:
        parsed = urlparse(url)
        host = parsed.hostname
        port = parsed.port or 6379
        if not host:
            return False
        socket.getaddrinfo(host, port, socket.AF_UNSPEC, socket.SOCK_STREAM)
        return True
    except OSError:
        return False


if broker_kind in {"stub", "memory", "inmemory"}:
    broker = StubBroker()
    logger.warning("Dramatiq broker backend: StubBroker (DRAMATIQ_BROKER={})", broker_kind)
elif _can_resolve_redis_host(redis_url):
    broker = RedisBroker(url=redis_url)
    logger.info("Dramatiq broker backend: RedisBroker ({})", redis_url)
else:
    broker = StubBroker()
    logger.warning(
        "Redis host from REDIS_URL is unavailable ({}). Using StubBroker fallback.",
        redis_url,
    )

dramatiq.set_broker(broker)
