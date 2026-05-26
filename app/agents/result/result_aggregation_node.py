"""
=============================================================================
Result Aggregation Node (agents/result/result_aggregation_node.py)
=============================================================================

【核心功能】
汇总 SQL 和 RAG 的结果，生成最终回复，并记录到记忆系统。

【工作流程】
sql_result + rag_result → 汇总 → 最终回复 → 记录到记忆

【感知/理解/执行】
- 感知: 接收 sql_result, rag_result, sql_error, critic_feedback
- 理解: 判断哪个结果可用，整合信息
- 执行: 生成最终回复，记录到 session_history
"""
from typing import Dict, Any, Optional

from langchain_core.messages import HumanMessage, SystemMessage

from app.agents.base.llm import create_chat_llm
from app.state.state import AgentState, WorkflowStep
from app.memory.short_term_memory import session_memory
from app.utils.logger import get_logger

logger = get_logger(__name__)


AGGREGATION_PROMPT = """你是质量检验知识库的回复聚合专家。

【用户问题】
{question}

【SQL 查询结果】
{sql_result}

【RAG 检索结果】
{rag_result}

【Critic 反馈】
{critic_feedback}

【你的任务】
1. 整合 SQL 和 RAG 的结果
2. 生成简洁、准确的最终回复
3. 如果有错误，说明原因

【输出格式】
直接输出回复内容，不要其他内容。
如果 SQL 执行失败且 RAG 无结果，说明无法回答。"""


async def result_aggregation_node(state: AgentState) -> AgentState:
    """
    Result Aggregation Node

    【感知】接收 sql_result, rag_result, sql_error, critic_feedback
    【理解】判断哪个结果可用，整合信息
    【执行】生成最终回复，记录到 session_history

    Args:
        state: AgentState

    Returns:
        更新后的 state，包含最终回复（通过 session_history 传递）
    """
    logger.info("Result Aggregation 开始汇总结果")

    question = state["question"]
    sql_domain = state.get("sql", {})
    rag_domain = state.get("rag", {})
    validation_domain = state.get("validation", {})
    sql_result = sql_domain.get("sql_result")
    sql_error = sql_domain.get("sql_error")
    rag_result = rag_domain.get("answer")
    critic_feedback = validation_domain.get("critic_feedback")
    session_id = state["session_id"]

    # 记录各状态信息
    if sql_result:
        logger.info(f"SQL result: success={sql_result.get('success')}, count={sql_result.get('count', 0)}")
    else:
        logger.info("SQL result: None")
    if sql_error:
        logger.warning(f"SQL error: {sql_error}")
    if rag_result:
        logger.info(f"RAG result: {rag_result[:50]}...")
    if critic_feedback:
        logger.info(f"Critic feedback: {critic_feedback}")

    # 生成最终回复
    logger.debug("调用 _generate_final_response 生成回复...")
    final_response = _generate_final_response(
        question=question,
        sql_result=sql_result,
        sql_error=sql_error,
        rag_result=rag_result,
        critic_feedback=critic_feedback,
        retry_exhausted=state.get("retry_exhausted", False),
        max_retries=state.get("max_retries", 2),
    )
    logger.debug(f"生成的回复长度: {len(final_response)} 字符")

    # 记录到记忆系统
    session_memory.add_message(session_id, "assistant", final_response)
    logger.info("Result Aggregation 完成，回复已记录到记忆系统")

    # 存储原始回复供后续优化
    return {
        **state,
        "result": {
            **state.get("result", {}),
            "raw_response": final_response,
        },
        "current_step": WorkflowStep.RESULT_AGGREGATION,
    }


def _generate_final_response(
    question: str,
    sql_result: Optional[dict],
    sql_error: Optional[str],
    rag_result: Optional[str],
    critic_feedback: Optional[str],
    retry_exhausted: bool = False,
    max_retries: int = 2,
) -> str:
    """
    生成最终回复

    Args:
        question: 用户问题
        sql_result: SQL 查询结果
        sql_error: SQL 错误信息
        rag_result: RAG 检索结果
        critic_feedback: Critic 反馈

    Returns:
        最终回复文本
    """
    # 情况1: SQL 执行成功
    if sql_result and sql_result.get("success"):
        data = sql_result.get("data", [])
        count = sql_result.get("count", 0)

        if count == 0:
            return "没有找到符合条件的数据。"

        # 构建回复
        lines = [f"找到 {count} 条结果：\n"]

        for i, row in enumerate(data[:10], 1):  # 最多显示10条
            lines.append(f"{i}. {repr(row)}")

        if count > 10:
            lines.append(f"\n... 还有 {count - 10} 条结果未显示")

        return "\n".join(lines)

    # 情况2: SQL 执行失败
    if sql_error:
        # 尝试用 RAG 结果补充
        if rag_result and rag_result != "RAG 功能待完善":
            return f"数据库查询失败：{sql_error}\n\n另外，关于您的问题：\n{rag_result}"

        return f"抱歉，无法回答您的问题。数据库查询失败：{sql_error}"

    # 情况3: 有 RAG 结果
    if rag_result and rag_result != "RAG 功能待完善":
        return rag_result

    # 情况4: 重试耗尽
    if retry_exhausted:
        return f"抱歉，经过 {max_retries} 次尝试后仍无法生成有效的 SQL。\n\nCritic 反馈：{critic_feedback or 'SQL 审查未通过'}"

    # 情况5: 全部失败
    return "抱歉，无法回答您的问题。请尝试重新描述您的问题。"