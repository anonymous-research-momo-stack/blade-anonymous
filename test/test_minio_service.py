import os
import tempfile
import unittest
from unittest.mock import Mock, patch

# 导入被测试的模块
from app.services.common.minio_service import (
    download_from_minio,
    upload_to_minio,
    minio_client
)


class TestMinioService(unittest.TestCase):
    """MinIO服务测试类"""

    def test_minio_connectivity(self):
        """测试MinIO是否能连通"""
        try:
            # 直接调用minio_client的list_buckets方法测试连通性
            minio_client.list_buckets()
            self.assertTrue(True, "MinIO连接正常")
        except Exception as e:
            self.fail(f"MinIO连接失败: {e}")

    def test_download_openssl_file(self):
        """测试能否从MinIO的task-files/openssl路径下载openssl文件到tmp文件夹"""
        try:
            # 直接调用download_from_minio函数
            result = download_from_minio("openssl")
            print(f"下载成功，文件路径: {result}")
            self.assertIsNotNone(result)
        except Exception as e:
            self.fail(f"下载openssl文件失败: {e}")

    def test_upload_analysis_result(self):
        """测试能否把tmp/analysis_result.json文件上传到MinIO的task-results/路径"""
        # 使用临时文件
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as temp_file:
            test_content = '{"test": "data"}'
            temp_file.write(test_content)
            temp_file_path = temp_file.name
        
        try:
            # 直接调用upload_to_minio函数，不指定第二个参数，让它使用默认行为
            result = upload_to_minio(temp_file_path)
            print(f"上传成功，文件路径: {result}")
            # 期望结果是临时文件的文件名
            expected_filename = os.path.basename(temp_file_path)
            self.assertEqual(result, expected_filename)
            
        except Exception as e:
            self.fail(f"上传analysis_result.json文件失败: {e}")
        finally:
            # 清理临时文件
            if os.path.exists(temp_file_path):
                os.remove(temp_file_path)


if __name__ == '__main__':
    # 运行测试
    unittest.main()
