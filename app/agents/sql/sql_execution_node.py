"""
=============================================================================
SQL Execution Node (agents/sql/sql_execution_node.py)
=============================================================================

【核心功能】
执行 SQL 查询并返回结果。

【工作流程】
generated_sql → SQL 执行 → sql_result / sql_error

【感知/理解/执行】
- 感知: 接收 generated_sql
- 理解: 理解 SQL 语义
- 执行: 调用数据库执行查询
"""
from typing import Dict, Any

from app.graph.state import AgentState, WorkflowStep
from app.tools.sql_validator import SQLValidator, SQLValidationError
from app.db.connection import fetch_all


class SQLExecutorNode:
    """SQL 执行 Node 工具类"""

    def __init__(self, max_rows: int = 100):
        self.max_rows = max_rows
        self.validator = SQLValidator()

    async def execute(self, sql: str) -> Dict[str, Any]:
        """
        执行 SQL 查询

        Args:
            sql: SQL 语句

        Returns:
            {"success": bool, "data": list, "count": int, "error": Optional[str]}
        """
        result = {
            "success": False,
            "data": None,
            "count": 0,
            "error": None,
        }

        try:
            # 校验 SQL
            self.validator.validate_and_sanitize(sql)

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


# 全局实例
sql_executor_node = SQLExecutorNode()


async def sql_execution_node(state: AgentState) -> AgentState:
    """
    SQL 执行 Node

    【感知】接收 generated_sql
    【理解】验证 SQL 安全性
    【执行】执行 SQL 查询

    Args:
        state: AgentState

    Returns:
        更新后的 state，包含 sql_result 或 sql_error
    """
    generated_sql = state.get("generated_sql")

    if not generated_sql:
        return {
            **state,
            "sql_result": None,
            "sql_error": "没有可执行的 SQL",
            "current_step": WorkflowStep.SQL_EXECUTION,
        }

    # 执行 SQL
    exec_result = await sql_executor_node.execute(generated_sql)

    return {
        **state,
        "sql_result": exec_result if exec_result["success"] else None,
        "sql_error": exec_result.get("error"),
        "current_step": WorkflowStep.SQL_EXECUTION,
    }