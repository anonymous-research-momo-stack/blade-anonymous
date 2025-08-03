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
    task_serializer='json',
    accept_content=['json'],
    result_serializer='json',
    timezone='Asia/Shanghai',
    enable_utc=True,
    task_hard_time_limit=6000,  # 设置任务硬超时为600秒
    task_routes={
        'app.celery_tasks.tpl_detection_task.tpl_detection_task': {'queue': 'tpl_detection_tasks'}
    }
)

# 自动发现任务
celery_app.autodiscover_tasks(['app.celery_tasks'])

# 手动导入任务模块，确保任务正确注册
from . import tpl_detection_task 