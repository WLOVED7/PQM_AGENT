"""
应用配置
所有敏感值从 .env 读取，不要硬编码
"""
from functools import lru_cache
from typing import Literal

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """应用配置"""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore"
    )

    # ===== 应用配置 =====
    APP_NAME: str = "质量检验知识库"
    APP_VERSION: str = "1.0.0"
    DEBUG: bool = False
    API_PREFIX: str = "/api/v1"

    # ===== 数据库配置 =====
    DB_HOST: str = ""
    DB_PORT: int = 3306
    DB_USER: str = ""
    DB_PASSWORD: str = ""
    DB_NAME: str = ""
    DB_CHARSET: str = "utf8mb4"

    # ===== 异步引擎配置 =====
    DB_POOL_SIZE: int = 10
    DB_MAX_OVERFLOW: int = 20
    DB_POOL_TIMEOUT: int = 30
    DB_POOL_RECYCLE: int = 3600

    # ===== LLM 配置 =====
    MiniMax_PROVIDER: str = "minimax"
    MiniMax_API_KEY: str = ""
    MiniMax_BASE_URL: str = ""
    MiniMax_MODEL: str = "MiniMax-M2.7"
    MiniMax_MAX_TOKENS: int = 4096
    MiniMax_TEMPERATURE: float = 0.7

    # ===== RagFlow 配置 =====
    RAGFLOW_BASE_URL: str = ""
    RAGFLOW_API_KEY: str = ""
    RAGFLOW_DATASET_ID: str = ""

    # ===== 日志配置 =====
    LOG_LEVEL: Literal["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"] = "INFO"
    LOG_FORMAT: str = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"

    # ===== 分页配置 =====
    DEFAULT_PAGE_SIZE: int = 20
    MAX_PAGE_SIZE: int = 100

    @property
    def DATABASE_URL(self) -> str:
        """异步数据库URL"""
        return (
            f"mysql+aiomysql://{self.DB_USER}:{self.DB_PASSWORD}"
            f"@{self.DB_HOST}:{self.DB_PORT}/{self.DB_NAME}"
            f"?charset={self.DB_CHARSET}"
        )


@lru_cache
def get_settings() -> Settings:
    """获取配置单例"""
    return Settings()


settings = get_settings()