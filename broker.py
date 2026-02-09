import dramatiq
import os
from dramatiq.brokers.redis import RedisBroker
from config import configure_logger, load_app_config

configure_logger()
config_data = load_app_config()

redis_url = os.getenv("REDIS_URL", config_data["redis_url"])
broker = RedisBroker(url=redis_url)
dramatiq.set_broker(broker)
