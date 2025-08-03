from celery import Celery
from ..config import settings

# 创建Celery应用实例
celery_app = Celery(
    "bsca_workflow",
    broker=settings.REDIS_BROKER_URL,
    backend=settings.REDIS_RESULT_BACKEND_URL
)

# Celery配置
celery_app.conf.update(
    task_track_started=True,
    # 可以添加更多配置
    # task_serializer='json',
    # accept_content=['json'],
    # result_serializer='json',
    # timezone='Asia/Shanghai',
    # enable_utc=True,
)

# 自动发现任务
celery_app.autodiscover_tasks(['app.celery_tasks']) 