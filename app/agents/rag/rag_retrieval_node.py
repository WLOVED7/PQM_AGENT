"""
=============================================================================
RAG Retrieval Node (agents/rag/rag_retrieval_node.py)
=============================================================================

【核心功能】
从 RagFlow 知识库检索相关文档，并生成答案。

【工作流程】
用户问题 → RagFlow 检索 → rag_result

【依赖】
需要配置 .env 中的 RAGFLOW_BASE_URL 和 RAGFLOW_API_KEY
"""
from app.state.state import AgentState, WorkflowStep
from app.tools.ragflow_client import rag_tool
from app.utils.logger import get_logger

logger = get_logger(__name__)


async def rag_retrieval_node(state: AgentState) -> AgentState:
    """
    RAG Retrieval Node

    【感知】接收 question
    【执行】调用 rag_tool 检索文档

    Args:
        state: AgentState

    Returns:
        更新后的 state，包含 rag_result
    """
    logger.info(f"RAG Retrieval 开始处理问题: {state['question'][:50]}...")

    question = state["question"]

    try:
        # 调用 rag_tool 执行检索（同步调用，内部处理异步）
        result = rag_tool.invoke(question)

        logger.info(f"RAG 检索完成，结果长度: {len(result)} 字符")

        return {
            "rag": {
                "retrieved_docs": [],
                "answer": result,
            },
            "current_step": WorkflowStep.RAG_RETRIEVAL,
        }

    except Exception as e:
        logger.error(f"RAG 检索失败: {e}")
        return {
            "rag": {
                "retrieved_docs": [],
                "answer": f"RAG 检索失败: {str(e)}",
            },
            "current_step": WorkflowStep.RAG_RETRIEVAL,
        }