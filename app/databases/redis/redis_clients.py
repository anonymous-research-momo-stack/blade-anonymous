import redis

from ...config import settings

# Connect to Redis for storing task metadata
tpl_detection_task_redis_client = redis.Redis(
    host=settings.REDIS_HOST,
    port=settings.REDIS_PORT,
    password=settings.REDIS_PASSWORD if settings.REDIS_PASSWORD else None,
    db=settings.REDIS_DB_METADATA
)