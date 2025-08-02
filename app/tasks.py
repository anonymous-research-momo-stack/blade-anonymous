from datetime import datetime

import redis
from celery import Celery

from .tpl_detection.detection_workflow import DetectionWorkflow

# 连接 Redis 用于存储任务元数据
redis_client = redis.Redis(host='bsca-expert-redis', port=6379, db=2)
broker_url = "redis://bsca-expert-redis:6379/0"
result_backend = "redis://bsca-expert-redis:6379/0"

celery_app = Celery(
    "bsca_workflow",
    broker=broker_url,
    backend=result_backend
)

celery_app.conf.update(
    task_track_started=True
)

# 注册任务
@celery_app.task
def analyze_task(file_path: str = "data/openssl"):
    task_start_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    # 将任务开始时间存储到 Redis
    redis_client.hset(f"task:{analyze_task.request.id}", "start_time", task_start_time)

    # TODO: workflow可以存储任务进度到redis db=2供查询
    workflow = DetectionWorkflow(
        enable_bin_info_analysis_web_search=False,
        feature_matching_return_top_n=5,
        debug_mode=False
    )
    result = workflow.run(file_path)
    result.task_id = result.task_id
    result.start_time = task_start_time

    result.analysis_data.preview()

    # result_file = f"analysis_result_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    result_file = analyze_task.request.id + datetime.now().strftime("%Y-%m-%d %H-%M-%S") +".json"
    result_save_path = "data/result" + result_file
    result.dump_to_file(result_save_path)

    return {"message": f"{file_path} 分析完成，结果已保存到 {result_save_path}",
            "binary_name": result.binary_name,
            'file_path': result_save_path,
            "start_time": task_start_time
            }
