from celery.result import AsyncResult
from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel
from ....celery_tasks.tpl_detection_task import tpl_detection_task, celery_app, tpl_detection_task_redis_client
from ....interface import TPLDetectionTask, TPLDetectionTaskStatus
import uuid
import json

router = APIRouter()


class TPLDetectionTaskRequest(BaseModel):
    """TPL检测任务请求模型"""
    file_minio_path: str


@router.post("/tpl_detection_task")    # 创建TPL检测任务
def create_tpl_detection_task(request: TPLDetectionTaskRequest):
    if not request.file_minio_path:
        raise HTTPException(status_code=400, detail="File path is required")
    
    print('Starting TPL detection task for file:', request.file_minio_path)
    
    try:
        # 1. 创建任务对象，赋值id
        task_id = str(uuid.uuid4())
        task = TPLDetectionTask(
            task_id=task_id,
            file_minio_path=request.file_minio_path,
            status=TPLDetectionTaskStatus.PENDING
        )
        
        # 2. 将task信息转换成json存储到redis中
        task_json = task.customer_serialize()
        tpl_detection_task_redis_client.set(task_id, json.dumps(task_json, ensure_ascii=False))
        
        # 3. 创建celery异步任务
        celery_task = tpl_detection_task.delay(task_id)
        
        # 4. 直接返回task的json
        return task_json
        
    except Exception as e:
        # 如果任务启动失败，返回错误信息
        raise HTTPException(status_code=500, detail=f"Task failed to start: {str(e)}")


@router.get("/tpl_detection_task/{task_id}")
def get_tpl_detection_task(task_id: str):
    """获取TPL检测任务信息"""
    redis_task_info = tpl_detection_task_redis_client.get(task_id)
    
    if not redis_task_info:
        raise HTTPException(status_code=404, detail="Task not found")
    
    try:
        task_info = json.loads(redis_task_info.decode('utf-8'))
        return task_info
    except json.JSONDecodeError:
        raise HTTPException(status_code=500, detail="Invalid task info format")


# 这里可以添加更多的API端点
# 例如：组件匹配、agent分析、workflow、评估等模块的API