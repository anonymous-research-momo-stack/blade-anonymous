import os

from pydantic_settings import BaseSettings
from environs import Env

env = Env()
env.read_env()

class Settings(BaseSettings):
    # --------- has default values ----------
    # Postgres
    POSTGRES_HOST: str = env.str("POSTGRES_HOST", "localhost")
    POSTGRES_PORT: int = env.int("POSTGRES_PORT", 2345)
    POSTGRES_USERNAME: str = env.str("POSTGRES_USERNAME", "open_binary_sca")
    POSTGRES_PASSWORD: str = env.str("POSTGRES_PASSWORD", "open_binary_sca")
    POSTGRES_DATABASE_MAIN: str = env.str("POSTGRES_DATABASE_MAIN", "open_binary_sca")
    POSTGRES_DATABASE_KNOWLEDGE: str = env.str("POSTGRES_DATABASE_KNOWLEDGE", "knowledge")


    MAIN_DATABASE_URL:str = f"postgresql+psycopg2://{POSTGRES_USERNAME}:{POSTGRES_PASSWORD}@{POSTGRES_HOST}:{POSTGRES_PORT}/{POSTGRES_DATABASE_MAIN}"
    KNOWLEDGE_DATABASE_URL:str = f"postgresql+psycopg2://{POSTGRES_USERNAME}:{POSTGRES_PASSWORD}@{POSTGRES_HOST}:{POSTGRES_PORT}/{POSTGRES_DATABASE_KNOWLEDGE}"

    # --------- Must Config ----------
    # Knowledge Files
    KNOWLEDGE_FILE_PATH: str = env.str("KNOWLEDGE_FILE_PATH")

# 创建全局配置实例
settings = Settings() 