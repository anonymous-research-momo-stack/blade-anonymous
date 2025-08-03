import os
import shutil
from datetime import datetime
from minio import Minio
from minio.error import S3Error

from ...config import settings

# 导入配置


# 初始化MinIO客户端
minio_client = Minio(
    settings.MINIO_ENDPOINT,
    access_key=settings.MINIO_ACCESS_KEY,
    secret_key=settings.MINIO_SECRET_KEY,
    secure=settings.MINIO_SECURE
)

# 导出常量供其他模块使用
LOCAL_TEMP_DIR = settings.LOCAL_TEMP_DIR




def download_from_minio(minio_file_path: str, download_dir: str = None) -> str:
    """
    从MinIO下载文件到本地临时目录

    Args:
        minio_file_path: MinIO中的文件路径（对象key）
        task_id: 任务ID，如果提供则下载到任务专用目录

    Returns:
        str: 本地文件的完整路径
    """
    try:
        file_name = os.path.basename(minio_file_path)
        local_file_path = os.path.join(download_dir, file_name)

        # 从MinIO下载文件
        minio_client.fget_object(settings.MINIO_INPUT_BUCKET, minio_file_path, local_file_path)

        print(f"文件已从MinIO下载到本地: {local_file_path}")
        return local_file_path

    except S3Error as e:
        raise Exception(f"从MinIO下载文件失败: {e}")
    except Exception as e:
        raise Exception(f"下载文件时发生错误: {e}")


def upload_to_minio(local_file_path: str, minio_file_path: str = None) -> str:
    """
    将本地文件上传到MinIO

    Args:
        local_file_path: 本地文件的完整路径
        minio_file_path: MinIO中的目标路径（对象key）
        cleanup_local: 是否清理本地文件

    Returns:
        str: MinIO中的文件路径
    """
    try:
        # 检查本地文件是否存在
        if not os.path.exists(local_file_path):
            raise FileNotFoundError(f"本地文件不存在: {local_file_path}")

        # 如果没有指定MinIO路径，使用本地文件名
        if minio_file_path is None:
            minio_file_path = os.path.basename(local_file_path)

        # 上传文件到MinIO
        minio_client.fput_object(settings.MINIO_OUTPUT_BUCKET, minio_file_path, local_file_path)

        print(f"文件已上传到MinIO: {minio_file_path}")

        return minio_file_path

    except S3Error as e:
        raise Exception(f"上传文件到MinIO失败: {e}")
    except Exception as e:
        raise Exception(f"上传文件时发生错误: {e}")


