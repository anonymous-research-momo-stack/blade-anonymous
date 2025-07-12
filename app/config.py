import os
from typing import Optional
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """应用配置类"""
    
    # 应用基本信息
    app_name: str = "BSCA Expert Agent API"
    app_version: str = "1.0.0"
    debug: bool = True
    
    # 服务器配置
    host: str = "0.0.0.0"
    port: int = 8000
    
    # 数据库配置
    database_url: str = "sqlite:///./bsca_expert_agent.db"
    
    # API配置
    api_key: Optional[str] = None
    
    # 日志配置
    log_level: str = "INFO"
    
    class Config:
        env_file = ".env"
        case_sensitive = False


# 创建全局配置实例
settings = Settings() 