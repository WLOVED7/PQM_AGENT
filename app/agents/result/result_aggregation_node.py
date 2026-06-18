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
- 执行: 生成最终回复，记录到 session_memory
"""
from typing import Dict, Any, Optional

from langchain_core.messages import HumanMessage, SystemMessage

from app.agents.base.llm import create_chat_llm
from app.state.state import AgentState, WorkflowStep, QueryIntent
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


META_HISTORY_PROMPT = """根据下面的对话历史，回答用户关于对话本身的问题。

【对话历史】
{history}

【用户当前问题】
{question}

【回答要求】
- 准确引用历史中的内容
- 简洁明了
- 如果历史不足以回答，说明"目前是本次对话的第一个问题"或类似话术

直接输出回答，不要其他内容。"""


GENERAL_LLM_PROMPT = """你是一个专注于质量管理与检验领域的智能助手，同时也具备通用知识。

【用户问题】
{question}

【你的任务】
直接用你的知识回答用户问题。
- 如果问题与质量检验/SIP/PQM相关，优先结合专业知识作答
- 如果是通用知识或闲聊，正常回答
- 回答简洁、准确，必要时分条说明

直接输出回答，不要其他内容。"""


async def result_aggregation_node(state: AgentState) -> AgentState:
    """
    Result Aggregation Node

    【感知】接收 sql_result, rag_result, sql_error, critic_feedback
    【理解】判断哪个结果可用，整合信息
    【执行】生成最终回复，记录到 session_memory
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
    intent = state.get("intent")

    # 元问题路径：直接用对话历史回答
    if intent == QueryIntent.META_HISTORY:
        logger.info("META_HISTORY 路径：使用对话历史生成回复")
        final_response = _answer_meta_question(question, session_id)
    # 通用 LLM 路径：直接调用 LLM 回答
    elif intent == QueryIntent.GENERAL_LLM:
        logger.info("GENERAL_LLM 路径：直接调用 LLM 回答")
        final_response = _answer_with_general_llm(question)
    else:
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

    return {
        "result": {"raw_response": final_response},
        "current_step": WorkflowStep.RESULT_AGGREGATION,
    }


def _answer_with_general_llm(question: str) -> str:
    """直接用 LLM 知识回答通用问题，不查数据库或知识库。"""
    llm = create_chat_llm()
    prompt = GENERAL_LLM_PROMPT.format(question=question)
    messages = [
        SystemMessage(content="你是一个专注于质量管理与检验领域的智能助手。"),
        HumanMessage(content=prompt),
    ]
    try:
        return llm.invoke(messages).strip()
    except Exception as e:
        logger.warning(f"通用 LLM 回答失败: {e}")
        return "抱歉，我暂时无法回答您的问题，请稍后重试。"


def _answer_meta_question(question: str, session_id: str) -> str:
    """
    回答关于对话历史的元问题。

    当前问题已被 coordinator 写入 session_memory，所以历史中最后一条 user 就是当前问题。
    LLM 需要识别这一点。
    """
    history = session_memory.get_history(session_id, limit=20)

    if len(history) <= 1:
        # 只有当前问题在历史里，没有更早的对话
        return "这是本次对话的第一个问题，暂无更早的对话历史。"

    lines = []
    for msg in history:
        role_label = "用户" if msg["role"] == "user" else "助手"
        lines.append(f"{role_label}: {msg['content']}")
    history_str = "\n".join(lines)

    llm = create_chat_llm()
    prompt = META_HISTORY_PROMPT.format(history=history_str, question=question)
    messages = [
        SystemMessage(content="你是一个对话助手，擅长回答关于对话历史的问题。"),
        HumanMessage(content=prompt),
    ]
    try:
        return llm.invoke(messages).strip()
    except Exception as e:
        logger.warning(f"元问题 LLM 调用失败，使用回退方案: {e}")
        # 回退：直接取倒数第二条 user 消息（"上一个问题"）
        user_msgs = [m for m in history if m["role"] == "user"]
        if len(user_msgs) >= 2:
            return f"您上一个问题是：{user_msgs[-2]['content']}"
        return "暂无历史问题。"


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
        logger.info("重试耗尽，使用通用 LLM 兜底回答")
        return _answer_with_general_llm(question)

    # 情况5: 全部失败，使用通用 LLM 兜底
    logger.info("SQL/RAG 均无结果，使用通用 LLM 兜底回答")
    return _answer_with_general_llm(question)