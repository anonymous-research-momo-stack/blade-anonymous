#!/bin/bash

# 启动脚本 - 同时运行FastAPI和Celery
# 基于FastAPI官方推荐和最佳实践

set -e

echo "开始启动 BSCA Expert Agent API 服务..."

# 等待Redis连接可用
echo "等待Redis连接..."
while ! redis-cli -h $REDIS_HOST -p $REDIS_PORT ping; do
  echo "Redis连接失败，等待重试..."
  sleep 2
done
echo "Redis连接成功!"

# 等待PostgreSQL连接可用
echo "等待PostgreSQL连接..."
while ! pg_isready -h $POSTGRES_HOST -p $POSTGRES_PORT -U $POSTGRES_USERNAME; do
  echo "PostgreSQL连接失败，等待重试..."
  sleep 2
done
echo "PostgreSQL连接成功!"

# 启动Celery worker在后台
echo "启动Celery worker..."
celery -A app.tasks worker --loglevel=info --concurrency=2 &
CELERY_PID=$!

# 等待一下让Celery启动
sleep 3

# 启动FastAPI应用
echo "启动FastAPI应用..."
exec fastapi run app/main.py --host 0.0.0.0 --port 8000

# 注意：使用exec确保FastAPI成为主进程，这样Docker可以正确处理信号
# 如果FastAPI退出，整个容器也会退出
# Celery worker会随着容器的结束而结束
