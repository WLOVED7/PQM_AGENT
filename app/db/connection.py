"""
=============================================================================
数据库连接层 (db/connection.py)
=============================================================================

使用 asyncpg 直连 PostgreSQL，不使用 ORM。

【为什么不用 ORM？】
- 工业场景 SQL 复杂，ORM 无法处理
- 直接 SQL 更灵活、更可控
- 减少抽象层，提高性能

【连接池管理】
- asyncpg 提供异步连接池
- 每次操作从池中获取连接，操作完归还

【注意】
- asyncpg 占位符格式为 $1, $2, ... (非 %s)
- fetch_* 返回 dict 列表，与原 aiomysql 接口保持一致
"""
import asyncpg
from typing import Optional, List, Dict, Any

from app.core.config import settings


class Database:
    """数据库连接管理器"""

    _pool: Optional[asyncpg.Pool] = None

    @classmethod
    async def get_pool(cls) -> asyncpg.Pool:
        """获取连接池（单例）"""
        if cls._pool is None:
            cls._pool = await asyncpg.create_pool(
                host=settings.DB_HOST,
                port=settings.DB_PORT,
                user=settings.DB_USER,
                password=settings.DB_PASSWORD,
                database=settings.DB_NAME,
                min_size=5,
                max_size=settings.DB_POOL_SIZE,
            )
        return cls._pool

    @classmethod
    async def close_pool(cls):
        """关闭连接池"""
        if cls._pool:
            await cls._pool.close()
            cls._pool = None

    @classmethod
    async def execute(cls, sql: str, params: tuple = None) -> int:
        """执行 SQL（INSERT/UPDATE/DELETE），返回影响行数"""
        pool = await cls.get_pool()
        args = params or ()
        result = await pool.execute(sql, *args)
        try:
            return int(result.split()[-1])
        except (ValueError, IndexError):
            return 0

    @classmethod
    async def fetch_one(cls, sql: str, params: tuple = None) -> Optional[Dict[str, Any]]:
        """查询单条记录"""
        pool = await cls.get_pool()
        args = params or ()
        row = await pool.fetchrow(sql, *args)
        return dict(row) if row else None

    @classmethod
    async def fetch_all(cls, sql: str, params: tuple = None) -> List[Dict[str, Any]]:
        """查询多条记录"""
        pool = await cls.get_pool()
        args = params or ()
        rows = await pool.fetch(sql, *args)
        return [dict(row) for row in rows]

    @classmethod
    async def fetch_many(cls, sql: str, params: tuple = None, size: int = 100) -> List[Dict[str, Any]]:
        """批量查询（限制返回行数）"""
        pool = await cls.get_pool()
        args = params or ()
        rows = await pool.fetch(sql, *args)
        return [dict(row) for row in rows[:size]]


# 快捷函数
async def execute(sql: str, params: tuple = None) -> int:
    return await Database.execute(sql, params)


async def fetch_one(sql: str, params: tuple = None) -> Optional[Dict[str, Any]]:
    return await Database.fetch_one(sql, params)


async def fetch_all(sql: str, params: tuple = None) -> List[Dict[str, Any]]:
    return await Database.fetch_all(sql, params)


async def fetch_many(sql: str, params: tuple = None, size: int = 100) -> List[Dict[str, Any]]:
    return await Database.fetch_many(sql, params, size)


async def close_db():
    await Database.close_pool()


async def init_db():
    await Database.get_pool()
