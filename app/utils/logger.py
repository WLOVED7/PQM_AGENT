"""
=============================================================================
日志模块 (utils/logger.py)
=============================================================================

【功能】
- 统一管理项目日志
- 日志仅写入文件，不输出到终端
- 支持按模块名称创建 logger

【日志文件】
- 位置：项目根目录下的 `logs/` 目录
- 文件名：`pqm.log`（所有模块共用一个日志文件）
- 轮转：使用 `RotatingFileHandler` 限制单文件最大 10MB，保留 5 个备份

【使用方式】
from app.utils.logger import get_logger

logger = get_logger(__name__)
logger.info("这是一条信息日志")
logger.error("这是一条错误日志")
"""
import logging
import os
from logging.handlers import RotatingFileHandler
from pathlib import Path

from app.core.config import settings


# 日志目录
LOG_DIR = Path(__file__).parent.parent.parent / "logs"
LOG_FILE = LOG_DIR / "pqm.log"

# 日志配置
_MAX_BYTES = 10 * 1024 * 1024  # 10MB per file
_BACKUP_COUNT = 5              # 保留 5 个备份文件


def _ensure_log_dir():
    """确保日志目录存在"""
    LOG_DIR.mkdir(parents=True, exist_ok=True)


def _create_file_handler() -> RotatingFileHandler:
    """
    创建文件 Handler（仅写入文件，不输出到终端）

    关键配置：
    - level: 从 settings.LOG_LEVEL 读取
    - formatter: 从 settings.LOG_FORMAT 读取
    - filename: logs/pqm.log
    """
    _ensure_log_dir()

    handler = RotatingFileHandler(
        filename=str(LOG_FILE),
        maxBytes=_MAX_BYTES,
        backupCount=_BACKUP_COUNT,
        encoding="utf-8",
    )

    handler.setLevel(getattr(logging, settings.LOG_LEVEL))

    # 使用配置文件中的格式
    formatter = logging.Formatter(settings.LOG_FORMAT)
    handler.setFormatter(formatter)

    return handler


def get_logger(name: str) -> logging.Logger:
    """
    获取指定名称的 logger

    Args:
        name: logger 名称，通常使用 __name__（模块路径）
              例如：app.agents.sql.sql_execution_node

    Returns:
        logging.Logger 实例

    【使用示例】
    logger = get_logger(__name__)
    logger.info("模块初始化")
    """
    logger = logging.getLogger(name)

    # 避免重复添加 handler
    if not logger.handlers:
        # 只添加 file handler，不添加 stream handler（终端不显示）
        logger.addHandler(_create_file_handler())

        # 设置 logger 级别
        logger.setLevel(getattr(logging, settings.LOG_LEVEL))

        # 防止日志向上传播到 root logger（避免重复输出）
        logger.propagate = False

    return logger
