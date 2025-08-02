import os
import tempfile
from minio import Minio
from minio.error import S3Error

# MinIO配置
MINIO_ENDPOINT = "MINIO_ENDPOINT"  # 例如: "localhost:9000"
MINIO_ACCESS_KEY = "MINIO_ACCESS_KEY"
MINIO_SECRET_KEY = "MINIO_SECRET_KEY"
MINIO_SECURE = False  # 是否使用HTTPS
INPUT_BUCKET = "INPUT_BUCKET"  # 输入文件的bucket
OUTPUT_BUCKET = "OUTPUT_BUCKET"  # 输出文件的bucket
LOCAL_TEMP_DIR = "LOCAL_TEMP_DIR"  # 本地临时目录

# 初始化MinIO客户端
minio_client = Minio(
    MINIO_ENDPOINT,
    access_key=MINIO_ACCESS_KEY,
    secret_key=MINIO_SECRET_KEY,
    secure=MINIO_SECURE
)


def download_from_minio(minio_file_path: str) -> str:
    """
    从MinIO下载文件到本地临时目录

    Args:
        minio_file_path: MinIO中的文件路径（对象key）

    Returns:
        str: 本地文件的完整路径
    """
    try:
        # 确保本地临时目录存在
        os.makedirs(LOCAL_TEMP_DIR, exist_ok=True)

        # 生成本地文件名（保持原文件名或生成唯一名称）
        file_name = os.path.basename(minio_file_path)
        if not file_name:
            file_name = f"temp_file_{datetime.now().strftime('%Y%m%d_%H%M%S')}"

        local_file_path = os.path.join(LOCAL_TEMP_DIR, file_name)

        # 从MinIO下载文件
        minio_client.fget_object(INPUT_BUCKET, minio_file_path, local_file_path)

        print(f"文件已从MinIO下载到本地: {local_file_path}")
        return local_file_path

    except S3Error as e:
        raise Exception(f"从MinIO下载文件失败: {e}")
    except Exception as e:
        raise Exception(f"下载文件时发生错误: {e}")


def upload_to_minio(local_file_path: str, minio_file_path: str) -> str:
    """
    将本地文件上传到MinIO

    Args:
        local_file_path: 本地文件的完整路径
        minio_file_path: MinIO中的目标路径（对象key）

    Returns:
        str: MinIO中的文件路径
    """
    try:
        # 检查本地文件是否存在
        if not os.path.exists(local_file_path):
            raise FileNotFoundError(f"本地文件不存在: {local_file_path}")

        # 上传文件到MinIO
        minio_client.fput_object(OUTPUT_BUCKET, minio_file_path, local_file_path)

        print(f"文件已上传到MinIO: {minio_file_path}")

        # 清理本地临时文件（可选）
        try:
            os.remove(local_file_path)
            print(f"已清理本地临时文件: {local_file_path}")
        except Exception as cleanup_error:
            print(f"清理临时文件失败: {cleanup_error}")

        return minio_file_path

    except S3Error as e:
        raise Exception(f"上传文件到MinIO失败: {e}")
    except Exception as e:
        raise Exception(f"上传文件时发生错误: {e}")