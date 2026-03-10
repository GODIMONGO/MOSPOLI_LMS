import dramatiq
from loguru import logger

from broker import broker


@dramatiq.actor(queue_name="for_test")
def broker_init_check():
    client = getattr(broker, "client", None)
    if client is not None:
        client.ping()
    logger.info("Запущен брокер и готов к работе.")
