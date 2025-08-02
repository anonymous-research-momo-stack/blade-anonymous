# 使用官方 Python 镜像
FROM python:3.11-slim

# 安装 strings 工具（在 binutils 包中）
RUN apt-get update && apt-get install -y binutils && rm -rf /var/lib/apt/lists/*

# 设置工作目录
WORKDIR /app

# 拷贝依赖文件
COPY ./requirements.txt .
# 安装依赖
RUN pip install --no-cache-dir -r requirements.txt

# 拷贝代码
COPY . .

ENV PYTHONUNBUFFERED=1
ENV PYTHONPATH=/app

EXPOSE 8000
