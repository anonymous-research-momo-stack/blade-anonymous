from celery.result import AsyncResult
from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel
from ...celery_tasks.celery_tasks import analyze_task, celery_app, redis_client

router = APIRouter()


class HealthResponse(BaseModel):
    """健康检查响应模型"""
    status: str
    version: str
    message: str


@router.get("/health", response_model=HealthResponse)
async def health_check():
    """健康检查端点"""
    return HealthResponse(
        status="healthy",
        version="1.0.0",
        message="BSCA Expert Agent API is running"
    )


@router.get("/")
async def root():
    """根端点"""
    return {
        "message": "BSCA Expert Agent API",
        "version": "1.0.0",
        "docs": "/docs"
    }

@router.get("/analyze/")    # 分析任务
def analyze(file_path: str = Query(..., description="文件路径")):
    if not file_path:
        raise HTTPException(status_code=400, detail="File path is required")
    print('Starting analysis for file:', file_path)
    try:
        # 启动异步任务
        task = analyze_task.delay(file_path)
    except Exception as e:
        # 如果任务启动失败，返回错误信息
        raise HTTPException(status_code=500, detail=f"Task failed to start: {str(e)}")
    return {"task_id": task.id}

@router.get("/status/")
def get_status(task_id: str):
    task_result = AsyncResult(task_id, app=celery_app)

    response =  {"task_id": task_id, "status": task_result.status}
    if task_result.status == 'PENDING':
        response["result"] = "任务还未提交或不存在"

    if task_result.status == 'STARTED':
        response["result"] = "任务已经开始"
        response["start_time"] = redis_client.hget(f"task:{task_id}", "start_time").decode('utf-8') if redis_client.hget(f"task:{task_id}", "start_time") else ''

    if task_result.status == 'SUCCESS':
        response["result"] = task_result.result.get('message', '')
        response['binary_name'] = task_result.result.get('binary_name', '')
        response['file_path'] = task_result.result.get('file_path', '')
        response['start_time'] = task_result.result.get('start_time', '')

    return response


# 这里可以添加更多的API端点
# 例如：组件匹配、agent分析、workflow、评估等模块的API