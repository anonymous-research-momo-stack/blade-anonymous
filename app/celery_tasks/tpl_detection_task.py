import os
import shutil
from datetime import datetime
import json
from celery.exceptions import SoftTimeLimitExceeded
from .celery_app import celery_app
from ..databases.redis.redis_clients import tpl_detection_task_redis_client
from ..services.common.minio_service import download_from_minio, upload_to_minio, LOCAL_TEMP_DIR
from ..services.tpl_detection.detection_workflow import DetectionWorkflow
from ..interface import TPLDetectionTaskStatus, TPLDetectionTask
from ..config import settings


def _get_task_from_redis(task_id: str) -> TPLDetectionTask:
    """从Redis中获取任务信息并初始化TPLDetectionTask对象"""
    task_info_json = tpl_detection_task_redis_client.get(task_id)
    if not task_info_json:
        error_msg = f"No task found for task_id: {task_id}"
        print(f"错误: {error_msg}")
        # 创建一个失败的任务对象，记录错误信息
        task = TPLDetectionTask(
            task_id=task_id,
            file_minio_path="",
            status=TPLDetectionTaskStatus.FAILED,
            error_message=error_msg,
            end_at=datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        )
        update_redis_task(task)
        return task
    
    try:
        task_info = json.loads(task_info_json.decode('utf-8'))
        return TPLDetectionTask.init_from_dict(task_info)
    except Exception as e:
        error_msg = f"Failed to parse task info for task_id {task_id}: {str(e)}"
        print(f"错误: {error_msg}")
        # 创建一个失败的任务对象，记录错误信息
        task = TPLDetectionTask(
            task_id=task_id,
            file_minio_path="",
            status=TPLDetectionTaskStatus.FAILED,
            error_message=error_msg,
            end_at=datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        )
        update_redis_task(task)
        return task


def update_redis_task(task: TPLDetectionTask):
    """更新Redis中的任务信息"""
    try:
        task_json = task.customer_serialize()
        tpl_detection_task_redis_client.set(task.task_id, json.dumps(task_json, ensure_ascii=False))
        print(f"任务 {task.task_id} 状态更新为: {task.status.value}")
    except Exception as e:
        print(f"错误: 更新Redis任务信息失败: {str(e)}")


def get_task_workspace_dir(task_id: str) -> str:
    """
    获取任务专用工作目录

    Args:
        task_id: 任务ID

    Returns:
        str: 任务专用目录的完整路径
    """
    task_dir = os.path.join(LOCAL_TEMP_DIR, task_id)
    os.makedirs(task_dir, exist_ok=True)
    return task_dir


def cleanup_task_workspace(task_id: str) -> bool:
    """
    清理任务专用工作目录

    Args:
        task_id: 任务ID

    Returns:
        bool: 清理是否成功
    """
    try:
        task_dir = get_task_workspace_dir(task_id)
        if os.path.exists(task_dir):
            shutil.rmtree(task_dir)
            print(f"已清理任务工作目录: {task_dir}")
            return True
        else:
            print(f"任务工作目录不存在: {task_dir}")
            return True
    except Exception as e:
        print(f"清理任务工作目录失败: {e}")
        return False

@celery_app.task
def tpl_detection_task(task_id: str):
    """TPL检测任务 - 只接收task_id参数"""
    print(f"开始处理任务: {task_id}")
    # 1. 从Redis获取任务信息并初始化对象
    task = _get_task_from_redis(task_id)
    if task.status == TPLDetectionTaskStatus.FAILED:
        # 如果任务初始化就失败了，直接返回task的JSON
        print(f"任务 {task_id} 初始化失败，返回错误信息")
        return task.customer_serialize()

    print(f"获取到任务: {task.task_id}, 文件路径: {task.file_minio_path}")

    # 2. 设置任务工作目录并更新任务开始时间和状态
    task.workspace_dir = get_task_workspace_dir(task_id)
    task.start_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    task.status = TPLDetectionTaskStatus.ANALYZING
    update_redis_task(task)

    print(f"任务工作目录: {task.workspace_dir}")

    try:
        # 3. 从MinIO下载文件到任务专用目录
        print(f"开始下载文件: {task.file_minio_path}")
        task.file_download_start_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        task.status = TPLDetectionTaskStatus.FILE_DOWNLOADING
        update_redis_task(task)

        # 使用任务ID下载到专用目录
        local_file_path = download_from_minio(task.file_minio_path, task.workspace_dir)

        task.file_download_end_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        task.file_local_path = local_file_path
        print(f"文件下载完成，本地路径: {local_file_path}")

        # 4. 开始分析
        print("开始TPL检测分析")
        task.analysis_start_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        task.status = TPLDetectionTaskStatus.ANALYZING
        update_redis_task(task)

        # 创建workflow实例
        workflow = DetectionWorkflow(
            enable_bin_info_analysis_web_search=False,
            feature_matching_return_top_n=5,
            debug_mode=False
        )

        # 使用本地文件路径进行分析
        result = workflow.run(local_file_path)

        print("保存分析结果到任务专用目录")

        # 生成结果文件名
        result_file = task.task_id + "_" + datetime.now().strftime("%Y-%m-%d_%H-%M-%S") + ".json"
        local_result_path = os.path.join(task.workspace_dir, result_file)

        # 保存结果到本地临时文件
        result.dump_to_file(local_result_path)
        task.analysis_end_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        # 5. 将分析结果上传到MinIO
        print("上传分析结果到MinIO")
        task.result_upload_start_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        task.result_local_path = local_result_path
        minio_result_path = result_file
        task.result_minio_path = minio_result_path  # 可以根据需要修改路径
        task.status = TPLDetectionTaskStatus.RESULT_UPLOADING
        update_redis_task(task)


        # 根据配置决定是否清理本地文件
        upload_to_minio(local_result_path, minio_result_path)

        task.result_upload_end_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        # 7. 更新任务状态为成功
        task.end_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        if result.error_message:
            task.error_message = result.error_message
            print(f"分析过程中出现错误: {result.error_message}")
            task.status = TPLDetectionTaskStatus.FAILED
        else:
            task.status = TPLDetectionTaskStatus.SUCCESS
        update_redis_task(task)

        print(f"任务完成，结果已保存到: {minio_result_path}")

        # 返回task的JSON
        return task.customer_serialize()
    except SoftTimeLimitExceeded:
        # 处理软超时 - 新添加的异常处理
        error_msg = f"任务超时: 任务执行时间超过600秒限制" # 在celery app 中设置。
        print(error_msg)

        task.end_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        task.error_message = error_msg
        task.status = TPLDetectionTaskStatus.FAILED
        update_redis_task(task)

        # 重要：确保返回task数据
        return task.customer_serialize()

    except Exception as e:
        # 记录失败信息
        error_msg = f"任务执行失败: {str(e)}"
        print(error_msg)
        
        task.end_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        task.error_message = error_msg
        task.status = TPLDetectionTaskStatus.FAILED
        
        # 更新任务状态为失败
        update_redis_task(task)

        # 返回task的JSON
        return task.customer_serialize()
    finally:
        # 8. 根据配置决定是否清理任务工作目录
        if settings.CLEANUP_ANALYSIS_FILES:
            cleanup_task_workspace(task_id)
            print(f"已清理任务工作目录: {task_id}")
