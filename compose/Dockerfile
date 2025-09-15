FROM tiangolo/uvicorn-gunicorn:python3.11

WORKDIR /app

# Install system dependency: unar
RUN apt-get update && apt-get install -y unar \
    && apt-get clean && rm -rf /var/lib/apt/lists/*

# Copy requirements.txt and install Python dependencies
COPY requirements.txt /tmp/
RUN pip install --no-cache-dir -r /tmp/requirements.txt

# Copy app code
COPY app /app/app

# Copy start script and grant execute permission
COPY compose/start.sh /app/start.sh
RUN chmod +x /app/start.sh

CMD ["/app/start.sh"]
