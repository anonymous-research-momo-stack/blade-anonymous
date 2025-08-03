import redis

from ...config import settings

# 连接 Redis 用于存储任务元数据
tpl_detection_task_redis_client = redis.Redis(
    host=settings.REDIS_HOST,
    port=settings.REDIS_PORT,
    password=settings.REDIS_PASSWORD if settings.REDIS_PASSWORD else None,
    db=settings.REDIS_DB_METADATA
)