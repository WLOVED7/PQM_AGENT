"""
=============================================================================
Critic Agent - SQL 质量审查 (agents/critic/critic_node.py)
=============================================================================

【核心功能】
验证生成的 SQL 是否正确、安全、能否回答用户问题。

【三层验证机制】
1. 基础安全校验 — 复用 SQLValidator（关键词/模式黑名单）
2. Schema 引用校验 — 表/字段是否存在
3. LLM 语义校验 — 判断 SQL 能否回答问题

【重试机制】
- needs_regeneration=True + retry_count < max → 重新生成
- needs_regeneration=True + retry_count >= max → 返回错误

【感知/理解/执行】
- 感知: 接收 question 和 generated_sql
- 理解: 验证 SQL 语法、语义、安全性
- 执行: 返回 sql_is_valid, critic_feedback, needs_regeneration
"""
from typing import Optional

from langchain_core.messages import HumanMessage, SystemMessage

from app.agents.base.llm import create_chat_llm
from app.graph.state import AgentState, WorkflowStep
from app.tools.sql_validator import SQLValidator, SQLValidationError
from app.tools.schema_loader import schema_loader


CRITIC_PROMPT = """你是 SQL 质量审查专家，负责验证生成的 SQL 是否正确。

【用户问题】
{question}

【生成的 SQL】
{generated_sql}

【Schema 上下文】
{schema_context}

【审查维度】
1. 正确性: SQL 能否正确回答用户问题
2. 安全性: 是否有 SQL 注入风险
3. 完整性: WHERE 条件是否完整
4. 效率: LIMIT 是否过大、是否有多余查询
5. 语法: SQL 语法是否正确

【无效的常见原因】
- 无法回答用户问题（如查询了错误的表/字段）
- JOIN 关系错误
- WHERE 条件遗漏
- LIMIT 过大（>100）
- 字段名/表名与 Schema 不符

【输出格式】
JSON: {{"is_valid": true/false, "feedback": "原因说明", "needs_regeneration": true/false}}"""


class CriticValidator:
    """Critic Agent 的验证工具"""

    def __init__(self):
        self.sql_validator = SQLValidator()
        self.allowed_tables = {"documents", "inspection_items", "document_changes"}

    def basic_security_check(self, sql: str) -> tuple:
        """
        第一层: 基础安全校验

        Returns:
            (is_valid, error_message)
        """
        try:
            self.sql_validator.validate_and_sanitize(sql)
            return True, None
        except SQLValidationError as e:
            return False, str(e)

    def schema_reference_check(self, sql: str) -> tuple:
        """
        第二层: Schema 引用校验

        检查 SQL 中引用的表是否在白名单中

        Returns:
            (is_valid, error_message)
        """
        import re

        # 提取 FROM 和 JOIN 后的表名
        tables = []
        patterns = [
            r'FROM\s+`?(\w+)`?',
            r'JOIN\s+`?(\w+)`?',
            r'LEFT\s+JOIN\s+`?(\w+)`?',
            r'RIGHT\s+JOIN\s+`?(\w+)`?',
            r'INNER\s+JOIN\s+`?(\w+)`?',
        ]

        for pattern in patterns:
            matches = re.findall(pattern, sql, re.IGNORECASE)
            tables.extend(matches)

        # 检查每个表是否在白名单
        for table in tables:
            if table.lower() not in self.allowed_tables:
                return False, f"禁止查询表: {table}"

        return True, None

    def semantic_check(self, question: str, sql: str, schema_context: str) -> dict:
        """
        第三层: LLM 语义校验

        判断 SQL 能否正确回答用户问题

        Returns:
            {"is_valid": bool, "feedback": str, "needs_regeneration": bool}
        """
        llm = create_chat_llm()

        prompt = CRITIC_PROMPT.format(
            question=question,
            generated_sql=sql,
            schema_context=schema_context,
        )

        messages = [
            SystemMessage(content="你是一个严格的 SQL 审查专家。"),
            HumanMessage(content=prompt),
        ]

        response = llm.invoke(messages)
        response_text = response.strip() if response else ""

        return _parse_critic_response(response_text)


def _parse_critic_response(response: str) -> dict:
    """
    解析 LLM 返回的审查结果

    Args:
        response: LLM 返回的文本

    Returns:
        {"is_valid": bool, "feedback": str, "needs_regeneration": bool}
    """
    result = {
        "is_valid": False,
        "feedback": "",
        "needs_regeneration": False,
    }

    response_lower = response.lower()

    # 解析 is_valid
    if "is_valid" in response_lower:
        # 检查是否明确包含 false
        if '"is_valid": false' in response_lower or "'is_valid': false" in response_lower:
            result["is_valid"] = False
        elif '"is_valid": true' in response_lower or "'is_valid': true" in response_lower:
            result["is_valid"] = True
        else:
            # 假设有 is_valid 关键字就是 true
            result["is_valid"] = True

    # 解析 needs_regeneration
    if "needs_regeneration" in response_lower:
        if '"needs_regeneration": true' in response_lower or "'needs_regeneration': true" in response_lower:
            result["needs_regeneration"] = True
        else:
            result["needs_regeneration"] = False

    # 提取 feedback（简单方法：取 JSON 部分之后的文本）
    if "feedback" in response_lower:
        # 尝试提取 feedback 的值
        import re
        match = re.search(r'feedback["\']?\s*:\s*["\']?([^"\'}]+)', response_lower)
        if match:
            result["feedback"] = match.group(1).strip()

    return result


async def critic_node(state: AgentState) -> AgentState:
    """
    Critic Node - SQL 质量审查

    【感知】接收 question 和 generated_sql
    【理解】三层验证（安全、Schema、语义）
    【执行】返回审查结果和反馈

    Args:
        state: AgentState

    Returns:
        更新后的 state，包含 sql_is_valid, critic_feedback, needs_regeneration
    """
    question = state["question"]
    generated_sql = state.get("generated_sql", "")

    # 如果没有 SQL，直接返回无效
    if not generated_sql:
        return {
            **state,
            "sql_is_valid": False,
            "critic_feedback": "没有可审查的 SQL",
            "needs_regeneration": True,
            "current_step": WorkflowStep.CRITIC_REVIEW,
        }

    # 创建验证器
    validator = CriticValidator()

    # 第一层: 基础安全校验
    is_valid, error = validator.basic_security_check(generated_sql)
    if not is_valid:
        return {
            **state,
            "sql_is_valid": False,
            "critic_feedback": f"安全校验失败: {error}",
            "needs_regeneration": True,
            "current_step": WorkflowStep.CRITIC_REVIEW,
        }

    # 第二层: Schema 引用校验
    is_valid, error = validator.schema_reference_check(generated_sql)
    if not is_valid:
        return {
            **state,
            "sql_is_valid": False,
            "critic_feedback": f"Schema 引用校验失败: {error}",
            "needs_regeneration": True,
            "current_step": WorkflowStep.CRITIC_REVIEW,
        }

    # 第三层: LLM 语义校验
    schema_context = schema_loader.generate_schema_context()
    semantic_result = validator.semantic_check(question, generated_sql, schema_context)

    return {
        **state,
        "sql_is_valid": semantic_result["is_valid"],
        "critic_feedback": semantic_result["feedback"] or "SQL 审查完成",
        "needs_regeneration": semantic_result["needs_regeneration"],
        "current_step": WorkflowStep.CRITIC_REVIEW,
    }