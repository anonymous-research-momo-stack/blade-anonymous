

import uvicorn
from fastapi import FastAPI

from .config import settings
from .api.v1.endpoints.tpl_detection_task import router


def create_app() -> FastAPI:
    
    app = FastAPI(
        title=settings.app_name,
        version=settings.app_version,
        description="BLADE",
        docs_url="/docs",
        redoc_url="/redoc"
    )

    

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