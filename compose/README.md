# BSCA Expert Agent API - Docker 部署指南

## 概述

本项目已按照 FastAPI 官方推荐的 Docker 最佳实践进行容器化改造。主要特性：

- **单容器运行**: FastAPI 和 Celery Worker 在同一容器中运行
- **健康检查**: 完整的容器健康检查机制
- **数据持久化**: 使用 Docker volumes 进行数据持久化
- **配置管理**: 环境变量配置，支持开发和生产环境

## 架构设计

```
┌─────────────────────┐    ┌─────────────────────┐    ┌─────────────────────┐
│  bsca-expert-app    │    │ bsca-expert-redis   │    │bsca-expert-postgres │
│                     │    │                     │    │                     │
│  ┌─────────────┐    │    │  Redis 7-alpine     │    │ PostgreSQL 16-alpine│
│  │  FastAPI    │────┼────┤  (消息代理/结果存储) │    │   (主数据库)        │
│  │             │    │    │                     │    │                     │
│  ├─────────────┤    │    └─────────────────────┘    └─────────────────────┘
│  │Celery Worker│    │
│  │             │    │
│  └─────────────┘    │
│                     │
└─────────────────────┘
```

## 快速开始

### 1. 准备工作

确保您的系统已安装：
- Docker (20.10+)
- Docker Compose (2.0+)

### 2. 配置环境变量

项目已包含预配置的 `.env.docker` 文件，包含您的 API 密钥和路径配置。如需自定义：

```bash
# 复制并编辑环境变量文件
cp .env.docker .env.custom
# 编辑 .env.custom 文件，修改 API 密钥等配置
```

### 3. 构建和启动服务

```bash
# 进入项目目录
cd /Users/liuchengyue/Desktop/BinarySCA\ Platform/Code/sca_agents/bsca-expert-agent-api

# 进入 compose 目录
cd compose

# 构建并启动所有服务
docker-compose -f docker-compose-all.yml up --build

# 或者在后台运行
docker-compose -f docker-compose-all.yml up --build -d
```

### 4. 验证部署

服务启动后，访问以下地址验证部署：

- **API 文档**: http://localhost:8000/docs
- **API 健康检查**: http://localhost:8000/api/v1/health
- **Redis**: localhost:6688 (如配置)
- **PostgreSQL**: localhost:2345 (如配置)

## 服务详情

### FastAPI + Celery 应用容器

- **容器名**: `bsca-expert-app`
- **端口**: 8000
- **功能**: 
  - FastAPI Web 服务
  - Celery Worker (异步任务处理)
  - 健康检查
- **数据卷**: 
  - `app_data:/data` (应用数据)
  - 时区同步

### Redis 服务

- **容器名**: `bsca-expert-redis`
- **镜像**: `redis:7-alpine`
- **端口**: 6379 (外部端口可配置)
- **功能**: Celery 消息代理和结果存储
- **数据持久化**: `redis_data` volume

### PostgreSQL 服务

- **容器名**: `bsca-expert-postgres`
- **镜像**: `postgres:16-alpine`
- **端口**: 5432 (外部端口可配置)
- **数据库**: `open_binary_sca`
- **数据持久化**: `postgres_data` volume

## 常用命令

### 查看服务状态
```bash
docker-compose -f docker-compose-all.yml ps
```

### 查看日志
```bash
# 查看所有服务日志
docker-compose -f docker-compose-all.yml logs

# 查看特定服务日志
docker-compose -f docker-compose-all.yml logs bsca-expert-app
docker-compose -f docker-compose-all.yml logs bsca-expert-redis
docker-compose -f docker-compose-all.yml logs bsca-expert-postgres

# 实时跟踪日志
docker-compose -f docker-compose-all.yml logs -f bsca-expert-app
```

### 重启服务
```bash
# 重启所有服务
docker-compose -f docker-compose-all.yml restart

# 重启特定服务
docker-compose -f docker-compose-all.yml restart bsca-expert-app
```

### 停止和清理
```bash
# 停止服务
docker-compose -f docker-compose-all.yml stop

# 停止并删除容器（保留数据卷）
docker-compose -f docker-compose-all.yml down

# 停止并删除容器和数据卷（谨慎使用！）
docker-compose -f docker-compose-all.yml down -v
```

### 进入容器调试
```bash
# 进入应用容器
docker exec -it bsca-expert-app bash

# 进入 PostgreSQL 容器
docker exec -it bsca-expert-postgres psql -U open_binary_sca -d open_binary_sca

# 进入 Redis 容器
docker exec -it bsca-expert-redis redis-cli
```

## API 使用示例

### 启动分析任务
```bash
curl -X POST "http://localhost:8000/api/v1/analyze/?file_path=data/openssl" \
     -H "accept: application/json"
```

### 查询任务状态
```bash
curl -X GET "http://localhost:8000/api/v1/status/?task_id=YOUR_TASK_ID" \
     -H "accept: application/json"
```

## 环境变量配置

主要配置项（在 `.env.docker` 中）：

### API 密钥
- `OPENAI_API_KEY`: OpenAI API 密钥
- `ANTHROPIC_API_KEY`: Anthropic API 密钥
- `BINARYAI_SECRET_ID/KEY`: BinaryAI 配置

### 应用配置
- `LLM_PROVIDER`: 语言模型提供商 (openai/anthropic)
- `LLM_MODEL_ID`: 模型 ID
- `APP_DEBUG`: 调试模式

### 端口配置
- `API_PORT`: API 服务端口 (默认 8000)
- `REDIS_PORT`: Redis 外部端口 (默认 6379)
- `POSTGRES_PORT`: PostgreSQL 外部端口 (默认 5432)

## 故障排除

### 常见问题

1. **容器启动失败**
   ```bash
   # 检查日志
   docker-compose -f docker-compose-all.yml logs bsca-expert-app
   
   # 检查端口占用
   lsof -i :8000
   ```

2. **数据库连接失败**
   ```bash
   # 检查 PostgreSQL 容器状态
   docker-compose -f docker-compose-all.yml logs bsca-expert-postgres
   
   # 手动测试数据库连接
   docker exec -it bsca-expert-postgres pg_isready -U open_binary_sca
   ```

3. **Redis 连接失败**
   ```bash
   # 检查 Redis 容器状态
   docker-compose -f docker-compose-all.yml logs bsca-expert-redis
   
   # 手动测试 Redis 连接
   docker exec -it bsca-expert-redis redis-cli ping
   ```

4. **健康检查失败**
   ```bash
   # 手动运行健康检查
   docker exec -it bsca-expert-app /code/healthcheck.sh
   ```

### 性能调优

1. **调整 Celery Worker 并发数**
   
   编辑 `start.sh`，修改 `--concurrency` 参数：
   ```bash
   celery -A app.tasks worker --loglevel=info --concurrency=4 &
   ```

2. **调整容器资源限制**
   
   在 `docker-compose-all.yml` 中添加：
   ```yaml
   deploy:
     resources:
       limits:
         memory: 2G
         cpus: '1.0'
   ```

## 开发模式

开发时可以挂载代码目录进行热更新：

```yaml
# 在 docker-compose-all.yml 的 bsca-expert-app 服务中添加
volumes:
  - ../app:/code/app  # 挂载源代码
  - app_data:/data
```

## 安全注意事项

1. **生产环境**：
   - 删除或替换 `.env.docker` 中的敏感信息
   - 使用更强的数据库密码
   - 配置防火墙规则
   - 启用 HTTPS

2. **API 密钥管理**：
   - 使用 Docker secrets 或外部密钥管理服务
   - 定期轮换 API 密钥

## 版本信息

- **FastAPI**: 0.116.1+
- **Python**: 3.11
- **Redis**: 7-alpine
- **PostgreSQL**: 16-alpine
- **Celery**: 5.5.3+
