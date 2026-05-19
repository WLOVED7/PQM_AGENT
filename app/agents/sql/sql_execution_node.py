"""
=============================================================================
SQL Execution Node (agents/sql/sql_execution_node.py)
=============================================================================

【核心功能】
执行已通过 Critic 审查的 SQL 查询。

【职责】
作为 Tool/节点，只负责执行 SQL。执行前 SQL 必须已经过 critic 审查。

【工作流程】
generated_sql (已审查) → 执行 SQL → sql_result / sql_error

【重要】
此节点在 critic 审查通过后才被执行，确保 SQL 安全有效后才执行。
"""
from app.graph.state import AgentState, WorkflowStep
from app.tools.sql_validator import SQLValidator, SQLValidationError
from app.db.connection import fetch_all


# 全局验证器
_validator = SQLValidator()


async def sql_execution_node(state: AgentState) -> AgentState:
    """
    SQL 执行 Node (Tool)

    【感知】接收 generated_sql (已通过 critic 审查)
    【执行】校验后执行 SQL 查询

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

    # 再次校验 SQL（安全双保险）
    try:
        _validator.validate_and_sanitize(generated_sql)
    except SQLValidationError as e:
        return {
            **state,
            "sql_result": None,
            "sql_error": f"SQL 校验失败: {str(e)}",
            "current_step": WorkflowStep.SQL_EXECUTION,
        }

    # 执行 SQL
    result = {
        "success": False,
        "sql": generated_sql,
        "data": None,
        "count": 0,
        "error": None,
    }

    try:
        data = await fetch_all(generated_sql)
        # 限制返回行数
        if len(data) > 100:
            data = data[:100]
        result["success"] = True
        result["data"] = data
        result["count"] = len(data)
    except Exception as e:
        result["error"] = f"SQL 执行失败: {str(e)}"

    return {
        **state,
        "sql_result": result if result["success"] else None,
        "sql_error": result.get("error"),
        "current_step": WorkflowStep.SQL_EXECUTION,
    }