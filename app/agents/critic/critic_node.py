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
- 执行: 返回 sql_valid, critic_feedback, needs_regeneration
"""
from typing import Optional

from langchain_core.messages import HumanMessage, SystemMessage

from app.agents.base.llm import create_chat_llm
from app.state.state import AgentState, WorkflowStep
from app.tools.sql_validator import SQLValidator, SQLValidationError
from app.tools.schema_loader import schema_loader
from app.utils.logger import get_logger

logger = get_logger(__name__)


CRITIC_PROMPT = """你是 SQL 质量审查专家，负责验证生成的 SQL 是否正确。

【用户问题】
{question}

【生成的 SQL】
{generated_sql}

【Schema 上下文】
{schema_context}

【审查原则】
1. **以用户问题为导向**：只关注 SQL 能否回答用户问题，不要过度要求无关字段
2. **安全校验**：检查 SQL 注入风险（黑名单关键词已由第一层校验）
3. **基本语法**：确保 SQL 语法正确、表名字段与 Schema 一致
4. **可执行性**：确保 SQL 能成功执行并返回结果

【宽容度】
- 如果 SQL 能回答用户的核心问题，即使缺少可选字段，也应判定为有效
- 不要因为"可能有用但用户未要求"的字段缺失而要求重试
- LIMIT 默认值 100 是合理的，不需要报错
- 只有当 SQL 无法回答用户问题时，才要求重试

【无效的判定标准】
- SQL 查询结果不能覆盖用户问题的核心需求
- 字段名/表名与 Schema 明显不符（唯一允许的表: sip_records）
- 使用了 JOIN 或引用了 sip_records 以外的表
- 存在 SQL 注入风险（第一层已校验，此条可不重复校验）

【输出格式】
JSON: {{"is_valid": true/false, "feedback": "原因说明", "needs_regeneration": true/false}}"""


class CriticValidator:
    """Critic Agent 的验证工具"""

    def __init__(self):
        self.sql_validator = SQLValidator()
        self.allowed_tables = {"sip_records"}

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
    import json
    import re

    result = {
        "is_valid": False,
        "feedback": "",
        "needs_regeneration": False,
    }

    # 优先尝试提取并解析完整 JSON 对象
    json_match = re.search(r'\{.*\}', response, re.DOTALL)
    if json_match:
        try:
            parsed = json.loads(json_match.group(0))
            result["is_valid"] = bool(parsed.get("is_valid", False))
            result["needs_regeneration"] = bool(parsed.get("needs_regeneration", False))
            result["feedback"] = str(parsed.get("feedback", "")).strip()
            return result
        except (json.JSONDecodeError, ValueError, TypeError) as e:
            logger.debug(f"JSON 解析失败，降级到字符串匹配: {e}")

    # Fallback: 字符串匹配（兼容 LLM 返回不规范 JSON 的情况）
    response_lower = response.lower()
    if '"is_valid": true' in response_lower or "'is_valid': true" in response_lower:
        result["is_valid"] = True
    if '"needs_regeneration": true' in response_lower or "'needs_regeneration': true" in response_lower:
        result["needs_regeneration"] = True

    fb_match = re.search(r'feedback["\']?\s*:\s*["\']([^"\']+)["\']', response)
    if fb_match:
        result["feedback"] = fb_match.group(1).strip()

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
        更新后的 state，包含 sql_valid, critic_feedback, needs_regeneration
    """
    logger.info("Critic 开始审查 SQL")
    question = state["question"]
    sql_domain = state.get("sql", {})
    generated_sql = sql_domain.get("generated_sql", "")

    # 如果没有 SQL，直接返回无效
    if not generated_sql:
        logger.warning("Critic 审查终止：没有可审查的 SQL")
        return {
            "sql": {"retry_count": sql_domain.get("retry_count", 0) + 1},
            "validation": {
                "sql_valid": False,
                "critic_feedback": "没有可审查的 SQL",
            },
            "current_step": WorkflowStep.CRITIC_REVIEW,
        }

    # 创建验证器
    validator = CriticValidator()

    # 第一层: 基础安全校验
    logger.debug("第一层：基础安全校验")
    is_valid, error = validator.basic_security_check(generated_sql)
    if not is_valid:
        logger.warning(f"第一层校验失败：{error}")
        return {
            "sql": {"retry_count": sql_domain.get("retry_count", 0) + 1},
            "validation": {
                "sql_valid": False,
                "critic_feedback": f"安全校验失败: {error}",
            },
            "current_step": WorkflowStep.CRITIC_REVIEW,
        }
    logger.debug("第一层校验通过")

    # 第二层: Schema 引用校验
    logger.debug("第二层：Schema 引用校验")
    is_valid, error = validator.schema_reference_check(generated_sql)
    if not is_valid:
        logger.warning(f"第二层校验失败：{error}")
        return {
            "sql": {"retry_count": sql_domain.get("retry_count", 0) + 1},
            "validation": {
                "sql_valid": False,
                "critic_feedback": f"Schema 引用校验失败: {error}",
            },
            "current_step": WorkflowStep.CRITIC_REVIEW,
        }
    logger.debug("第二层校验通过")

    # 第三层: LLM 语义校验
    logger.debug("第三层：LLM 语义校验")
    schema_context = schema_loader.generate_schema_context()
    semantic_result = validator.semantic_check(question, generated_sql, schema_context)
    logger.info(f"LLM 语义校验完成：is_valid={semantic_result['is_valid']}, needs_regeneration={semantic_result['needs_regeneration']}, feedback={semantic_result.get('feedback', '')}")

    if not semantic_result["is_valid"]:
        logger.warning(f"SQL 语义审查未通过：{semantic_result.get('feedback', '未知原因')}")

    return {
        "sql": {"retry_count": sql_domain.get("retry_count", 0) + 1},
        "validation": {
            "sql_valid": semantic_result["is_valid"],
            "critic_feedback": semantic_result["feedback"] or "SQL 审查完成",
        },
        "current_step": WorkflowStep.CRITIC_REVIEW,
    }