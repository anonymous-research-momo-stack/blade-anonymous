#!/bin/bash

# BSCA Expert Agent API - 部署测试脚本
# 用于验证 Docker 容器化部署是否成功

set -e

echo "🚀 开始测试 BSCA Expert Agent API 部署..."

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# 测试函数
test_service() {
    local service_name=$1
    local test_command=$2
    local description=$3
    
    echo -e "${BLUE}📋 测试: ${description}${NC}"
    
    if eval $test_command; then
        echo -e "${GREEN}✅ ${service_name} 测试通过${NC}"
        return 0
    else
        echo -e "${RED}❌ ${service_name} 测试失败${NC}"
        return 1
    fi
}

# 等待函数
wait_for_service() {
    local service_url=$1
    local service_name=$2
    local max_attempts=30
    local attempt=1
    
    echo -e "${YELLOW}⏳ 等待 ${service_name} 启动...${NC}"
    
    while [ $attempt -le $max_attempts ]; do
        if curl -s -f "$service_url" > /dev/null 2>&1; then
            echo -e "${GREEN}✅ ${service_name} 已就绪${NC}"
            return 0
        fi
        
        echo "尝试 $attempt/$max_attempts - 等待 ${service_name}..."
        sleep 2
        ((attempt++))
    done
    
    echo -e "${RED}❌ ${service_name} 启动超时${NC}"
    return 1
}

echo -e "${BLUE}===========================================${NC}"
echo -e "${BLUE}     BSCA Expert Agent API 部署测试${NC}"
echo -e "${BLUE}===========================================${NC}"

# 1. 检查 Docker 服务状态
echo -e "${YELLOW}🔍 检查 Docker 容器状态...${NC}"
if ! docker-compose -f docker-compose-all.yml ps; then
    echo -e "${RED}❌ 无法获取容器状态，请先启动服务${NC}"
    echo "运行: docker-compose -f docker-compose-all.yml up -d"
    exit 1
fi

# 2. 等待服务启动
wait_for_service "http://localhost:8000/api/v1/health" "FastAPI 应用"

# 3. 测试健康检查端点
test_service "健康检查" \
    "curl -s -f http://localhost:8000/api/v1/health | grep -q 'healthy'" \
    "API 健康检查端点"

# 4. 测试 API 文档页面
test_service "API文档" \
    "curl -s -f http://localhost:8000/docs > /dev/null" \
    "Swagger API 文档页面"

# 5. 测试根端点
test_service "根端点" \
    "curl -s -f http://localhost:8000/api/v1/ | grep -q 'BSCA Expert Agent API'" \
    "API 根端点响应"

# 6. 测试 Redis 连接
test_service "Redis连接" \
    "docker exec bsca-expert-redis redis-cli ping | grep -q 'PONG'" \
    "Redis 服务连接"

# 7. 测试 PostgreSQL 连接
test_service "PostgreSQL连接" \
    "docker exec bsca-expert-postgres pg_isready -U open_binary_sca | grep -q 'accepting connections'" \
    "PostgreSQL 数据库连接"

# 8. 测试容器健康状态
echo -e "${BLUE}📋 检查容器健康状态${NC}"
healthy_containers=$(docker-compose -f docker-compose-all.yml ps --format "table {{.Name}}\t{{.State}}" | grep -c "running\|healthy" || true)
total_containers=$(docker-compose -f docker-compose-all.yml ps --format "table {{.Name}}" | wc -l)

if [ "$healthy_containers" -ge 3 ]; then
    echo -e "${GREEN}✅ 所有关键容器都在运行${NC}"
else
    echo -e "${RED}❌ 部分容器未正常运行${NC}"
fi

# 9. 测试 Celery 任务队列（可选）
echo -e "${BLUE}📋 测试 Celery 任务提交...${NC}"
if curl -s -X POST "http://localhost:8000/api/v1/analyze/?file_path=test" | grep -q "task_id"; then
    echo -e "${GREEN}✅ Celery 任务提交成功${NC}"
else
    echo -e "${YELLOW}⚠️  Celery 任务提交可能需要额外配置${NC}"
fi

# 10. 显示服务信息
echo -e "${BLUE}===========================================${NC}"
echo -e "${BLUE}           部署测试完成${NC}"
echo -e "${BLUE}===========================================${NC}"
echo -e "${GREEN}🌐 服务访问地址:${NC}"
echo -e "   • API 文档: http://localhost:8000/docs"
echo -e "   • API 根地址: http://localhost:8000/api/v1/"
echo -e "   • 健康检查: http://localhost:8000/api/v1/health"
echo ""
echo -e "${GREEN}📊 服务状态:${NC}"
docker-compose -f docker-compose-all.yml ps

echo ""
echo -e "${GREEN}🎉 BSCA Expert Agent API 部署测试完成！${NC}"
echo -e "${BLUE}如需查看日志，运行: docker-compose -f docker-compose-all.yml logs -f${NC}"
