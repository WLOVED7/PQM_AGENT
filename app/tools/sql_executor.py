"""
=============================================================================
SQL 执行器 (tools/sql_executor.py)
=============================================================================

【核心功能】
执行 SQL 查询并返回结果。

【工作流程】
1. 接收 SQL
2. 校验 SQL 安全性
3. 执行查询
4. 返回结果
"""

from typing import List, Dict, Any, Optional
from app.db.connection import fetch_one, fetch_all, fetch_many
from app.tools.sql_validator import sql_validator, SQLValidationError


class SQLExecutor:
    """SQL 执行器"""

    def __init__(self, max_rows: int = 100):
        """
        初始化执行器

        Args:
            max_rows: 最大返回行数
        """
        self.max_rows = max_rows

    async def execute(self, sql: str) -> Dict[str, Any]:
        """
        执行 SQL 查询

        Args:
            sql: SQL 语句

        Returns:
            {
                "success": bool,
                "sql": str,
                "data": List[Dict],
                "count": int,
                "error": Optional[str]
            }

        Raises:
            SQLValidationError: SQL 校验失败
        """
        result = {
            "success": False,
            "sql": sql,
            "data": None,
            "count": 0,
            "error": None,
        }

        try:
            # 校验 SQL
            sql_validator.validate_and_sanitize(sql)

            # 执行查询
            data = await fetch_all(sql)

            # 限制返回行数
            if len(data) > self.max_rows:
                data = data[:self.max_rows]

            result["success"] = True
            result["data"] = data
            result["count"] = len(data)

        except SQLValidationError as e:
            result["error"] = f"SQL 校验失败: {str(e)}"
        except Exception as e:
            result["error"] = f"SQL 执行失败: {str(e)}"

        return result

    async def execute_one(self, sql: str) -> Dict[str, Any]:
        """
        执行 SQL 查询，返回单条结果

        Args:
            sql: SQL 语句

        Returns:
            单条记录或 None
        """
        try:
            sql_validator.validate_and_sanitize(sql)
            return await fetch_one(sql)
        except SQLValidationError:
            return None
        except Exception:
            return None


# 全局实例
sql_executor = SQLExecutor()
