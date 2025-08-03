FROM tiangolo/uvicorn-gunicorn:python3.11

WORKDIR /app

# 安装系统依赖： unar
RUN apt-get update && apt-get install -y unar \
    && apt-get clean && rm -rf /var/lib/apt/lists/*

# 复制requirements.txt 并安装python依赖
COPY requirements/* /tmp/
RUN pip install --no-cache-dir -r /tmp/linux_mac.txt


# 复制app代码
COPY app /app/app


# 复制启动脚本，并赋予执行权限
COPY scripts/start.sh /app/start.sh
RUN chmod +x /app/start.sh

CMD ["/app/start.sh"]
