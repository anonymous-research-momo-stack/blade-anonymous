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

    MAIN_DATABASE_URL:str = f"postgresql+psycopg2://{POSTGRES_USERNAME}:{POSTGRES_PASSWORD}@{POSTGRES_HOST}:{POSTGRES_PORT}/{POSTGRES_DATABASE_MAIN}"
    KNOWLEDGE_DATABASE_URL:str = f"postgresql+psycopg2://{POSTGRES_USERNAME}:{POSTGRES_PASSWORD}@{POSTGRES_HOST}:{POSTGRES_PORT}/{POSTGRES_DATABASE_KNOWLEDGE}"

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

# 创建全局配置实例
settings = Settings() 