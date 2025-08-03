import time
import sys
import os

# 添加项目根目录到Python路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from app.api.v1.endpoints.tpl_detection_task import create_tpl_detection_task, get_tpl_detection_task
from app.api.v1.endpoints.tpl_detection_task import TPLDetectionTaskRequest

def test_tpl_detection():
    """测试TPL检测任务"""
    print("🚀 启动TPL检测任务测试...")
    
    # 1. 调用第一个函数启动任务，获取ID
    request = TPLDetectionTaskRequest(file_minio_path="openssl")
    result = create_tpl_detection_task(request)
    task_id = result['task_id']
    print(f"✅ 任务创建成功，ID: {task_id}")
    
    # 2. while循环调用第二个函数，监听任务状态
    print("🔍 开始监听任务状态...")
    while True:
        task_info = get_tpl_detection_task(task_id)
        status = task_info['status']
        print(f"📊 当前状态: {status}")
        
        if status in ['success', 'failed']:
            print(f"🎯 任务完成，最终状态: {status}")
            break
        
        time.sleep(1)

if __name__ == '__main__':
    test_tpl_detection() 