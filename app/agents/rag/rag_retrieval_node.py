"""
=============================================================================
RAG Retrieval Node (agents/rag/rag_retrieval_node.py)
=============================================================================

【核心功能】
从知识库检索相关文档，并生成答案。

【工作流程】
用户问题 → 检索相关文档 → 生成答案 → rag_result

【注意】
当前为占位实现，向量检索后续添加。

【感知/理解/执行】
- 感知: 接收 question 和 session_history
- 理解: 理解查询意图，检索相关文档
- 执行: 返回检索到的文档和生成的答案
"""
from typing import Optional

from langchain_core.messages import HumanMessage, SystemMessage

from app.agents.base.llm import create_chat_llm
from app.state.state import AgentState, WorkflowStep
from app.memory.short_term_memory import session_memory
from app.utils.logger import get_logger

logger = get_logger(__name__)


RAG_PROMPT = """你是质量检验知识库的文档检索专家。

【用户问题】
{question}

【你的任务】
1. 理解用户问题
2. 回答用户问题（基于你知道的质检知识）

【重要】
- 如果不知道答案，明确说明"我无法回答这个问题"
- 不要编造或推测不确定的信息
- 回答要简洁、准确

【输出格式】
直接输出答案，不要其他内容。"""


async def rag_retrieval_node(state: AgentState) -> AgentState:
    """
    RAG Retrieval Node

    【感知】接收 question 和 session_history
    【理解】理解查询意图
    【执行】检索文档（当前为占位）并生成答案

    Args:
        state: AgentState

    Returns:
        更新后的 state，包含 retrieved_docs 和 rag_result
    """
    logger.info(f"RAG Retrieval 开始处理问题: {state['question'][:50]}...")

    llm = create_chat_llm()
    question = state["question"]
    session_id = state["session_id"]

    # 获取对话历史上下文
    history_context = session_memory.get_context_for_llm(session_id, limit=3)

    # 构建消息
    messages = [
        SystemMessage(content=RAG_PROMPT.format(question=question)),
    ]

    if history_context:
        messages.append(HumanMessage(content=f"【对话历史】\n{history_context}"))

    # 调用 LLM 生成答案（当前无实际文档检索）
    logger.debug("调用 LLM 生成 RAG 答案...")
    answer = llm.invoke(messages)
    answer = answer.strip() if answer else ""
    logger.info(f"RAG 检索完成，结果长度: {len(answer)} 字符")

    return {
        **state,
        "rag": {
            **state.get("rag", {}),
            "retrieved_docs": [],  # 占位：后续接入向量数据库
            "answer": answer or "RAG 功能待完善",
        },
        "current_step": WorkflowStep.RAG_RETRIEVAL,
    }