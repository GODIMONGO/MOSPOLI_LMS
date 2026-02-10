import dramatiq
from loguru import logger

from broker import broker


@dramatiq.actor(queue_name="for_test")
def broker_init_check():
    broker.client.ping()
    logger.info("Запущен брокер и готов к работе.")
