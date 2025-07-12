import os
from typing import Optional
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """应用配置类"""
    
    POSTGRES_HOST: str = os.getenv("POSTGRES_HOST", "localhost")
    POSTGRES_PORT: int = int(os.getenv("POSTGRES_PORT", 2345))
    POSTGRES_USERNAME: str = os.getenv("POSTGRES_USERNAME", "open_binary_sca")
    POSTGRES_PASSWORD: str = os.getenv("POSTGRES_PASSWORD", "open_binary_sca")
    POSTGRES_DATABASE: str = os.getenv("POSTGRES_DATABASE", "open_binary_sca")


# 创建全局配置实例
settings = Settings() 