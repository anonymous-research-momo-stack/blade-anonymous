"""
BSCA Expert Agent API
二进制软件成分分析专家代理API
"""

import uvicorn
from fastapi import FastAPI

from .config import settings
from .api.v1.endpoints.tpl_detection_task import router


def create_app() -> FastAPI:
    """创建FastAPI应用"""
    
    app = FastAPI(
        title=settings.app_name,
        version=settings.app_version,
        description="二进制软件成分分析专家代理API",
        docs_url="/docs",
        redoc_url="/redoc"
    )

    
    # 注册路由
    app.include_router(router, prefix="/api/v1")
    
    return app


app = create_app()


if __name__ == "__main__":
    uvicorn.run(
        "main:app",
        host=settings.host,
        port=settings.port,
        reload=settings.debug
    )