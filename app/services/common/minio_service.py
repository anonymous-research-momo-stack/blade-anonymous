import os
import shutil
from datetime import datetime
from minio import Minio
from minio.error import S3Error

from ...config import settings

# Import configuration


# Initialize MinIO client
minio_client = Minio(
    settings.MINIO_ENDPOINT,
    access_key=settings.MINIO_ACCESS_KEY,
    secret_key=settings.MINIO_SECRET_KEY,
    secure=settings.MINIO_SECURE
)

# Export constants for other modules
LOCAL_TEMP_DIR = settings.LOCAL_TEMP_DIR




def download_from_minio(minio_file_path: str, download_dir: str = None) -> str:
    """
    Download a file from MinIO to a local temporary directory.

    Args:
        minio_file_path: Object key (file path) in MinIO.
        task_id: Task ID; if provided, download to a task-specific directory.

    Returns:
        str: Full path to the local file.
    """
    try:
        file_name = os.path.basename(minio_file_path)
        local_file_path = os.path.join(download_dir, file_name)

        # Download file from MinIO
        minio_client.fget_object(settings.MINIO_INPUT_BUCKET, minio_file_path, local_file_path)

        print(f"File downloaded from MinIO to local: {local_file_path}")
        return local_file_path

    except S3Error as e:
        raise Exception(f"Failed to download file from MinIO: {e}")
    except Exception as e:
        raise Exception(f"An error occurred while downloading the file: {e}")


def upload_to_minio(local_file_path: str, minio_file_path: str = None) -> str:
    """
    Upload a local file to MinIO.

    Args:
        local_file_path: Full path to the local file.
        minio_file_path: Target object key (path) in MinIO.
        cleanup_local: Whether to clean up the local file after upload.

    Returns:
        str: File path (object key) in MinIO.
    """
    try:
        # Check whether the local file exists
        if not os.path.exists(local_file_path):
            raise FileNotFoundError(f"Local file does not exist: {local_file_path}")

        # If no MinIO path is provided, use the local filename
        if minio_file_path is None:
            minio_file_path = os.path.basename(local_file_path)

        # Upload file to MinIO
        minio_client.fput_object(settings.MINIO_OUTPUT_BUCKET, minio_file_path, local_file_path)

        print(f"File uploaded to MinIO: {minio_file_path}")

        return minio_file_path

    except S3Error as e:
        raise Exception(f"Failed to upload file to MinIO: {e}")
    except Exception as e:
        raise Exception(f"An error occurred while uploading the file: {e}")


