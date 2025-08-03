import os

from pydantic_settings import BaseSettings
from environs import Env

env = Env()
env.read_env()


class Settings(BaseSettings):
    # --------- has default values ----------
    # use_new_database
    use_new_database: bool = env.bool("USE_NEW_DATABASE", False)

    # Postgres
    POSTGRES_HOST: str = env.str("POSTGRES_HOST", "localhost")
    POSTGRES_PORT: int = env.int("POSTGRES_PORT", 2345)
    POSTGRES_USERNAME: str = env.str("POSTGRES_USERNAME", "open_binary_sca")
    POSTGRES_PASSWORD: str = env.str("POSTGRES_PASSWORD", "open_binary_sca")
    POSTGRES_DATABASE_MAIN: str = env.str("POSTGRES_DATABASE_MAIN", "open_binary_sca")
    POSTGRES_DATABASE_KNOWLEDGE: str = env.str("POSTGRES_DATABASE_KNOWLEDGE", "knowledge")

    MAIN_DATABASE_URL: str = f"postgresql+psycopg2://{POSTGRES_USERNAME}:{POSTGRES_PASSWORD}@{POSTGRES_HOST}:{POSTGRES_PORT}/{POSTGRES_DATABASE_MAIN}"
    KNOWLEDGE_DATABASE_URL: str = f"postgresql+psycopg2://{POSTGRES_USERNAME}:{POSTGRES_PASSWORD}@{POSTGRES_HOST}:{POSTGRES_PORT}/{POSTGRES_DATABASE_KNOWLEDGE}"

    # --------- Redis Configuration ----------
    REDIS_HOST: str = env.str("REDIS_HOST", "bsca-expert-redis")
    REDIS_PORT: int = env.int("REDIS_PORT", 6379)
    REDIS_PASSWORD: str = env.str("REDIS_PASSWORD", "")
    REDIS_DB_BROKER: int = env.int("REDIS_DB_BROKER", 0)  # Celery broker
    REDIS_DB_RESULT: int = env.int("REDIS_DB_RESULT", 0)  # Celery result backend
    REDIS_DB_METADATA: int = env.int("REDIS_DB_METADATA", 2)  # 任务元数据存储

    # --------- MinIO Configuration ----------
    MINIO_ENDPOINT: str = env.str("MINIO_ENDPOINT", "localhost:9000")
    MINIO_ACCESS_KEY: str = env.str("MINIO_ACCESS_KEY", "")
    MINIO_SECRET_KEY: str = env.str("MINIO_SECRET_KEY", "")
    MINIO_SECURE: bool = env.bool("MINIO_SECURE", False)
    MINIO_INPUT_BUCKET: str = env.str("MINIO_INPUT_BUCKET", "input-files")
    MINIO_OUTPUT_BUCKET: str = env.str("MINIO_OUTPUT_BUCKET", "output-results")
    LOCAL_TEMP_DIR: str = env.str("LOCAL_TEMP_DIR", "/tmp/")
    
    # --------- Analysis Configuration ----------
    CLEANUP_ANALYSIS_FILES: bool = env.bool("CLEANUP_ANALYSIS_FILES", True)  # 是否清理分析过程文件

    # --------- LLM Configuration ----------
    # LLM Provider: "openai", "anthropic", "ollama"
    LLM_PROVIDER: str = env.str("LLM_PROVIDER", "openai")
    # Model ID for the selected provider
    LLM_MODEL_ID: str = env.str("LLM_MODEL_ID", "gpt-4.1")
    # API Keys
    OPENAI_API_KEY: str = env.str("OPENAI_API_KEY", "")
    ANTHROPIC_API_KEY: str = env.str("ANTHROPIC_API_KEY", "")
    # Ollama configuration
    OLLAMA_BASE_URL: str = env.str("OLLAMA_BASE_URL", "http://localhost:11434")

    # --------- Must Config ----------
    # Knowledge Files
    KNOWLEDGE_FILE_PATH: str = env.str("KNOWLEDGE_FILE_PATH")

    # --------- Api Config ----------
    app_name: str = env.str("APP_NAME", "BSCA Expert Agent API")
    app_version: str = env.str("APP_VERSION", "0.1.0")
    host: str = env.str("APP_HOST", "0.0.0.0")
    port: int = env.int("APP_PORT", 8000)
    debug: bool = env.bool("APP_DEBUG", False)

    # --------- Computed Properties ----------
    @property
    def REDIS_BROKER_URL(self) -> str:
        """Celery broker URL"""
        if self.REDIS_PASSWORD:
            return f"redis://:{self.REDIS_PASSWORD}@{self.REDIS_HOST}:{self.REDIS_PORT}/{self.REDIS_DB_BROKER}"
        return f"redis://{self.REDIS_HOST}:{self.REDIS_PORT}/{self.REDIS_DB_BROKER}"

    @property
    def REDIS_RESULT_BACKEND_URL(self) -> str:
        """Celery result backend URL"""
        if self.REDIS_PASSWORD:
            return f"redis://:{self.REDIS_PASSWORD}@{self.REDIS_HOST}:{self.REDIS_PORT}/{self.REDIS_DB_RESULT}"
        return f"redis://{self.REDIS_HOST}:{self.REDIS_PORT}/{self.REDIS_DB_RESULT}"


# 创建全局配置实例
settings = Settings()