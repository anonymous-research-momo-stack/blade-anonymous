from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Dict, Any

router = APIRouter()


class HealthResponse(BaseModel):
    """健康检查响应模型"""
    status: str
    version: str
    message: str


@router.get("/health", response_model=HealthResponse)
async def health_check():
    """健康检查端点"""
    return HealthResponse(
        status="healthy",
        version="1.0.0",
        message="BSCA Expert Agent API is running"
    )


@router.get("/")
async def root():
    """根端点"""
    return {
        "message": "BSCA Expert Agent API",
        "version": "1.0.0",
        "docs": "/docs"
    }


# 这里可以添加更多的API端点
# 例如：组件匹配、agent分析、workflow、评估等模块的API 