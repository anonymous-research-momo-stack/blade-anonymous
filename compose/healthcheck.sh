#!/bin/bash

# 健康检查脚本 - 检查FastAPI应用是否正常运行
# 用于Docker容器的健康检查

set -e

# 使用Python内置的urllib模块检查健康状态，避免依赖curl
python3 -c "
import urllib.request
import sys
import json

try:
    response = urllib.request.urlopen('http://localhost:8000/api/v1/health', timeout=5)
    if response.status == 200:
        data = json.loads(response.read().decode('utf-8'))
        if data.get('status') == 'healthy':
            print('Health check passed')
            sys.exit(0)
        else:
            print('Health check failed: unhealthy status')
            sys.exit(1)
    else:
        print(f'Health check failed: HTTP {response.status}')
        sys.exit(1)
except Exception as e:
    print(f'Health check failed: {e}')
    sys.exit(1)
"
