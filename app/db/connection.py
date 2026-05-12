"""
=============================================================================
数据库连接层 (db/connection.py)
=============================================================================

使用 aiomysql 直连，不使用 ORM。

【为什么不用 ORM？】
- 工业场景 SQL 复杂，ORM 无法处理
- 直接 SQL 更灵活、更可控
- 减少抽象层，提高性能

【连接池管理】
- aiomysql 提供异步连接池
- 每次操作从池中获取连接，操作完归还
"""
import aiomysql
from typing import Optional, List, Dict, Any
from contextlib import asynccontextmanager

from app.core.config import settings


class Database:
    """数据库连接管理器"""

    _pool: Optional[aiomysql.Pool] = None

    @classmethod
    async def get_pool(cls) -> aiomysql.Pool:
        """获取连接池（单例）"""
        if cls._pool is None:
            cls._pool = await aiomysql.create_pool(
                host=settings.DB_HOST,
                port=settings.DB_PORT,
                user=settings.DB_USER,
                password=settings.DB_PASSWORD,
                db=settings.DB_NAME,
                minsize=5,
                maxsize=settings.DB_POOL_SIZE,
                autocommit=False,
                charset="utf8mb4",
            )
        return cls._pool

    @classmethod
    async def close_pool(cls):
        """关闭连接池"""
        if cls._pool:
            cls._pool.close()
            await cls._pool.wait_closed()
            cls._pool = None

    @classmethod
    @asynccontextmanager
    async def get_connection(cls):
        """获取数据库连接（上下文管理器）"""
        pool = await cls.get_pool()
        async with pool.acquire() as conn:
            async with conn.cursor(aiomysql.DictCursor) as cursor:
                yield conn, cursor

    @classmethod
    async def execute(cls, sql: str, params: tuple = None) -> int:
        """执行 SQL（INSERT/UPDATE/DELETE），返回影响行数"""
        async with cls.get_connection() as (conn, cursor):
            await cursor.execute(sql, params)
            await conn.commit()
            return cursor.rowcount

    @classmethod
    async def fetch_one(cls, sql: str, params: tuple = None) -> Optional[Dict[str, Any]]:
        """查询单条记录"""
        async with cls.get_connection() as (conn, cursor):
            await cursor.execute(sql, params)
            return await cursor.fetchone()

    @classmethod
    async def fetch_all(cls, sql: str, params: tuple = None) -> List[Dict[str, Any]]:
        """查询多条记录"""
        async with cls.get_connection() as (conn, cursor):
            await cursor.execute(sql, params)
            return await cursor.fetchall()

    @classmethod
    async def fetch_many(cls, sql: str, params: tuple = None, size: int = 100) -> List[Dict[str, Any]]:
        """批量查询"""
        async with cls.get_connection() as (conn, cursor):
            await cursor.execute(sql, params)
            return await cursor.fetchmany(size)


# 快捷函数
async def execute(sql: str, params: tuple = None) -> int:
    """执行 SQL"""
    return await Database.execute(sql, params)


async def fetch_one(sql: str, params: tuple = None) -> Optional[Dict[str, Any]]:
    """查询单条"""
    return await Database.fetch_one(sql, params)


async def fetch_all(sql: str, params: tuple = None) -> List[Dict[str, Any]]:
    """查询全部"""
    return await Database.fetch_all(sql, params)


async def fetch_many(sql: str, params: tuple = None, size: int = 100) -> List[Dict[str, Any]]:
    """批量查询"""
    return await Database.fetch_many(sql, params, size)


async def close_db():
    """关闭数据库连接池"""
    await Database.close_pool()


async def init_db():
    """初始化数据库（检查连接）"""
    await Database.get_pool()
