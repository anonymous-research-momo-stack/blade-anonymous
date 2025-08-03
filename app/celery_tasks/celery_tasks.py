import os
from datetime import datetime

import redis
from celery import Celery

from ..services.common.minio_service import download_from_minio, LOCAL_TEMP_DIR, upload_to_minio
from ..services.tpl_detection.detection_workflow import DetectionWorkflow
from ..config import settings

# 连接 Redis 用于存储任务元数据
redis_client = redis.Redis(
    host=settings.REDIS_HOST,
    port=settings.REDIS_PORT,
    password=settings.REDIS_PASSWORD if settings.REDIS_PASSWORD else None,
    db=settings.REDIS_DB_METADATA
)

celery_app = Celery(
    "bsca_workflow",
    broker=settings.REDIS_BROKER_URL,
    backend=settings.REDIS_RESULT_BACKEND_URL
)

celery_app.conf.update(
    task_track_started=True
)


@celery_app.task
def analyze_task(file_path: str = "data/openssl"):
    task_start_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    # 将任务开始时间存储到 Redis
    redis_client.hset(f"task:{analyze_task.request.id}", "start_time", task_start_time)

    local_file_path = None
    try:
        # 1. 从MinIO下载文件到本地
        local_file_path = download_from_minio(file_path)

        # TODO: workflow可以存储任务进度到redis db=2供查询
        workflow = DetectionWorkflow(
            enable_bin_info_analysis_web_search=False,
            feature_matching_return_top_n=5,
            debug_mode=False
        )

        # 使用本地文件路径进行分析
        result = workflow.run(local_file_path)
        result.task_id = analyze_task.request.id
        result.start_time = task_start_time

        result.analysis_data.preview()

        # 生成结果文件名
        result_file = analyze_task.request.id + "_" + datetime.now().strftime("%Y-%m-%d_%H-%M-%S") + ".json"
        local_result_path = os.path.join(LOCAL_TEMP_DIR, result_file)

        # 保存结果到本地临时文件
        result.dump_to_file(local_result_path)

        # 2. 将分析结果上传到MinIO
        minio_result_path = f"results/{result_file}"  # 可以根据需要调整路径结构
        upload_to_minio(local_result_path, minio_result_path)

        return {
            "message": f"{file_path} 分析完成，结果已保存到 MinIO: {minio_result_path}",
            "binary_name": result.binary_name,
            'file_path': minio_result_path,  # 返回MinIO路径
            "start_time": task_start_time
        }

    except Exception as e:
        # 清理可能的本地临时文件
        if local_file_path and os.path.exists(local_file_path):
            try:
                os.remove(local_file_path)
            except:
                pass
        raise e