"""
应用配置
"""
from functools import lru_cache
from typing import Literal

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """应用配置"""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore"
    )

    # 应用配置
    APP_NAME: str = "质量检验知识库"
    APP_VERSION: str = "1.0.0"
    DEBUG: bool = False
    API_PREFIX: str = "/api/v1"

    # 数据库配置
    DB_HOST: str = "localhost"
    DB_PORT: int = 3306
    DB_USER: str = "root"
    DB_PASSWORD: str = "123456"
    DB_NAME: str = "pqm_db"
    DB_CHARSET: str = "utf8mb4"

    # 异步引擎配置
    DB_POOL_SIZE: int = 10
    DB_MAX_OVERFLOW: int = 20
    DB_POOL_TIMEOUT: int = 30
    DB_POOL_RECYCLE: int = 3600

    @property
    def DATABASE_URL(self) -> str:
        """异步数据库URL"""
        return (
            f"mysql+aiomysql://{self.DB_USER}:{self.DB_PASSWORD}"
            f"@{self.DB_HOST}:{self.DB_PORT}/{self.DB_NAME}"
            f"?charset={self.DB_CHARSET}"
        )

    @property
    def SYNC_DATABASE_URL(self) -> str:
        """同步数据库URL (用于Alembic)"""
        return (
            f"mysql+pymysql://{self.DB_USER}:{self.DB_PASSWORD}"
            f"@{self.DB_HOST}:{self.DB_PORT}/{self.DB_NAME}"
            f"?charset={self.DB_CHARSET}"
        )

    # 日志配置
    LOG_LEVEL: Literal["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"] = "INFO"
    LOG_FORMAT: str = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"

    # 分页配置
    DEFAULT_PAGE_SIZE: int = 20
    MAX_PAGE_SIZE: int = 100

    # LLM 配置
    LLM_PROVIDER: str = "anthropic"  # anthropic / openai
    LLM_API_KEY: str = "sk-cp-4gzfAGOzIult6JekIzI-w02HG-kkdF2Gd4mQp4-MWAcdY7cNbBs3mjtQmOe0u-CJ0P6Rod_wpgEe9aCeRL3aUSYPnISn0k2dEGT2JDTWOW0RFBTEGX5VnLA"
    LLM_BASE_URL: str = "https://api.minimaxi.com/anthropic"
    LLM_MODEL: str = "MiniMax-M2.7"
    LLM_MAX_TOKENS: int = 4096
    LLM_TEMPERATURE: float = 0.7


@lru_cache
def get_settings() -> Settings:
    """获取配置单例"""
    return Settings()


settings = get_settings()
