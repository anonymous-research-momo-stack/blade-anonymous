# 使用官方 Python 镜像（按照FastAPI官方推荐）
FROM python:3.11-slim

# 安装系统依赖：strings 工具（在 binutils 包中）和其他必要工具
RUN apt-get update && apt-get install -y \
    binutils \
    curl \
    postgresql-client \
    redis-tools \
    && rm -rf /var/lib/apt/lists/*

# 设置工作目录（按照FastAPI官方推荐使用/code）
WORKDIR /code

# 先复制requirements.txt以利用Docker缓存
COPY ./requirements.txt /code/requirements.txt

# 安装Python依赖（按照FastAPI官方推荐）
RUN pip install --no-cache-dir --upgrade -r /code/requirements.txt

# 复制应用代码和配置文件
COPY ./app /code/app
COPY ./.env.docker /code/.env

# 创建数据目录并复制必要的数据文件
RUN mkdir -p /data/knowledge /data/evaluation /data/test_cases
COPY ./data/knowledge_jsons /data/knowledge/
COPY ./evaluation /data/evaluation/

# 设置环境变量
ENV PYTHONUNBUFFERED=1
ENV PYTHONPATH=/code

# 复制启动脚本和健康检查脚本
COPY ./compose/start.sh /code/start.sh
COPY ./compose/healthcheck.sh /code/healthcheck.sh
RUN chmod +x /code/start.sh /code/healthcheck.sh

# 暴露端口
EXPOSE 8000

# 使用启动脚本同时运行FastAPI和Celery
CMD ["/code/start.sh"]
