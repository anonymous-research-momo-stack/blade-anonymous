#!/bin/bash

# BSCA Expert Agent API - 快速启动脚本
# 一键启动整个 BSCA 专家代理系统

set -e

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}===========================================${NC}"
echo -e "${BLUE}    BSCA Expert Agent API 快速启动${NC}"
echo -e "${BLUE}===========================================${NC}"

# 检查 Docker 是否运行
if ! docker info > /dev/null 2>&1; then
    echo -e "${RED}❌ Docker 未运行，请先启动 Docker${NC}"
    exit 1
fi

echo -e "${GREEN}✅ Docker 服务正常${NC}"

# 检查端口占用
check_port() {
    local port=$1
    if lsof -i :$port > /dev/null 2>&1; then
        echo -e "${YELLOW}⚠️  端口 $port 已被占用${NC}"
        read -p "是否继续？ (y/N): " -n 1 -r
        echo
        if [[ ! $REPLY =~ ^[Yy]$ ]]; then
            exit 1
        fi
    fi
}

echo -e "${BLUE}🔍 检查端口占用...${NC}"
check_port 8000
check_port 6688
check_port 2345

# 构建并启动服务
echo -e "${BLUE}🚀 构建和启动 Docker 服务...${NC}"
echo -e "${YELLOW}这可能需要几分钟时间（首次构建）...${NC}"

if docker-compose -f docker-compose-all.yml up --build -d; then
    echo -e "${GREEN}✅ 服务启动成功${NC}"
else
    echo -e "${RED}❌ 服务启动失败${NC}"
    echo -e "${BLUE}查看错误日志:${NC}"
    docker-compose -f docker-compose-all.yml logs
    exit 1
fi

# 等待服务就绪
echo -e "${BLUE}⏳ 等待服务就绪...${NC}"
sleep 10

# 检查服务状态
echo -e "${BLUE}📊 当前服务状态:${NC}"
docker-compose -f docker-compose-all.yml ps

# 运行测试
echo -e "${BLUE}🧪 运行部署测试...${NC}"
if [ -f "./test_deployment.sh" ]; then
    ./test_deployment.sh
else
    echo -e "${YELLOW}⚠️  测试脚本未找到，手动验证服务${NC}"
    
    # 简单的健康检查
    echo -e "${BLUE}📋 基本健康检查...${NC}"
    sleep 5
    
    if curl -s -f http://localhost:8000/api/v1/health > /dev/null; then
        echo -e "${GREEN}✅ API 服务正常${NC}"
    else
        echo -e "${RED}❌ API 服务异常${NC}"
    fi
fi

echo -e "${BLUE}===========================================${NC}"
echo -e "${GREEN}🎉 BSCA Expert Agent API 启动完成！${NC}"
echo -e "${BLUE}===========================================${NC}"

echo -e "${GREEN}📱 快速访问链接:${NC}"
echo -e "   🌐 API 文档: ${BLUE}http://localhost:8000/docs${NC}"
echo -e "   🏠 API 主页: ${BLUE}http://localhost:8000/api/v1/${NC}"
echo -e "   💚 健康检查: ${BLUE}http://localhost:8000/api/v1/health${NC}"

echo ""
echo -e "${GREEN}📚 常用命令:${NC}"
echo -e "   📄 查看日志: ${YELLOW}docker-compose -f docker-compose-all.yml logs -f${NC}"
echo -e "   📊 查看状态: ${YELLOW}docker-compose -f docker-compose-all.yml ps${NC}"
echo -e "   🛑 停止服务: ${YELLOW}docker-compose -f docker-compose-all.yml down${NC}"
echo -e "   🔄 重启服务: ${YELLOW}docker-compose -f docker-compose-all.yml restart${NC}"

echo ""
echo -e "${GREEN}🔧 开发调试:${NC}"
echo -e "   🐳 进入应用容器: ${YELLOW}docker exec -it bsca-expert-app bash${NC}"
echo -e "   🗄️  连接数据库: ${YELLOW}docker exec -it bsca-expert-postgres psql -U open_binary_sca -d open_binary_sca${NC}"
echo -e "   📦 连接Redis: ${YELLOW}docker exec -it bsca-expert-redis redis-cli${NC}"

echo ""
echo -e "${BLUE}系统已就绪，开始您的二进制软件成分分析之旅！${NC}"
