"""
=============================================================================
LangGraph State 定义 (state/state.py)
=============================================================================

【用途】
定义多 Agent 系统的共享状态，所有节点通过这个状态通信。

【状态设计原则 - 业务域隔离】
- 全局共享: question, session_id, current_step, intent
- SQL Domain: generated_sql, sql_result, sql_error, retry_count
- RAG Domain: retrieved_docs, reranked_docs, answer
- Validation Domain: sql_valid, hallucination_score, critic_feedback
- Result Domain: raw_response, final_response
"""
from typing import TypedDict, Annotated, Optional
from enum import Enum

from app.state.reducers import merge_reducer


class QueryIntent(str, Enum):
    """查询意图枚举"""
    DATABASE_QUERY = "database_query"
    DOCUMENT_SEARCH = "document_search"
    MIXED = "mixed"
    META_HISTORY = "meta_history"
    GENERAL_LLM = "general_llm"
    UNKNOWN = "unknown"


class WorkflowStep(str, Enum):
    """工作流步骤枚举"""
    COORDINATOR = "coordinator"
    SQL_GENERATION = "sql_generation"
    CRITIC_REVIEW = "critic_review"
    SQL_EXECUTION = "sql_execution"
    RAG_RETRIEVAL = "rag_retrieval"
    RESULT_AGGREGATION = "result_aggregation"
    RESPONSE_OPTIMIZATION = "response_optimization"


# ===== 业务域类型 =====


class SQLState(TypedDict):
    """SQL 业务域状态"""
    generated_sql: Optional[str]
    sql_result: Optional[dict]
    sql_error: Optional[str]
    retry_count: int


class RAGState(TypedDict):
    """RAG 业务域状态"""
    retrieved_docs: Optional[list]
    reranked_docs: Optional[list]
    answer: Optional[str]


class ValidationState(TypedDict):
    """校验域状态"""
    sql_valid: bool
    hallucination_score: Optional[float]
    critic_feedback: Optional[str]


class ResultState(TypedDict):
    """结果域状态"""
    raw_response: Optional[str]
    final_response: Optional[str]


class AgentState(TypedDict):
    """
    LangGraph 多 Agent 系统共享状态

    【结构 - 业务域隔离】
    - 全局共享: question, session_id, current_step, intent, global_context
    - SQL Domain: SQL 生成和执行相关状态
    - RAG Domain: RAG 检索相关状态
    - Validation Domain: SQL/RAG 校验相关状态
    - Result Domain: 最终结果相关状态
    """

    # === 全局共享 ===
    question: str
    session_id: str
    intent: str          # 存字符串值，避免 Enum 类型引发 msgpack 反序列化警告
    current_step: str    # 同上
    global_context: Annotated[dict, merge_reducer]

    # === 业务域 ===
    sql: Annotated[SQLState, merge_reducer]
    rag: Annotated[RAGState, merge_reducer]
    validation: Annotated[ValidationState, merge_reducer]
    result: Annotated[ResultState, merge_reducer]

    # === 工作流控制 ===
    max_retries: int
    error: Optional[str]
    retry_exhausted: bool


def create_initial_state(
    question: str,
    session_id: str,
    max_retries: int = 2,
) -> AgentState:
    """
    创建初始状态

    Args:
        question: 用户问题
        session_id: Session ID
        max_retries: 最大重试次数

    Returns:
        初始化的 AgentState
    """
    return AgentState(
        question=question,
        session_id=session_id,
        intent=QueryIntent.UNKNOWN,
        current_step=WorkflowStep.COORDINATOR,
        global_context={},
        sql={
            "generated_sql": None,
            "sql_result": None,
            "sql_error": None,
            "retry_count": 0,
        },
        rag={
            "retrieved_docs": None,
            "reranked_docs": None,
            "answer": None,
        },
        validation={
            "sql_valid": False,
            "hallucination_score": None,
            "critic_feedback": None,
        },
        result={
            "raw_response": None,
            "final_response": None,
        },
        max_retries=max_retries,
        error=None,
        retry_exhausted=False,
    )