"""
=============================================================================
LangGraph State 定义 (graph/state.py)
=============================================================================

【用途】
定义多 Agent 系统的共享状态，所有节点通过这个状态通信。

【状态设计原则】
- 感知 (Perception): question, session_history
- 理解 (Understanding): intent, use_sql, use_rag
- 执行 (Execution): generated_sql, sql_result, sql_is_valid
- 记忆 (Memory): session_history, session_id
"""
from typing import TypedDict, Annotated, Optional, Literal
from enum import Enum

from langgraph.graph import add_messages


class QueryIntent(str, Enum):
    """查询意图枚举"""
    DATABASE_QUERY = "database_query"
    DOCUMENT_SEARCH = "document_search"
    MIXED = "mixed"
    UNKNOWN = "unknown"


class WorkflowStep(str, Enum):
    """工作流步骤枚举"""
    COORDINATOR = "coordinator"
    SQL_AGENT = "sql_agent"
    CRITIC_REVIEW = "critic_review"
    RAG_RETRIEVAL = "rag_retrieval"
    RESULT_AGGREGATION = "result_aggregation"


class AgentState(TypedDict):
    """
    LangGraph 多 Agent 系统共享状态

    【结构】
    - 用户输入: question, session_id
    - 意图分发: intent, use_sql, use_rag
    - SQL 工作流: generated_sql, sql_result, sql_is_valid
    - RAG 工作流: retrieved_docs, rag_result
    - Critic 反馈: critic_feedback, needs_regeneration
    - 记忆系统: session_history
    - 工作流控制: current_step, retry_count, max_retries, error
    """

    # === 用户输入 ===
    question: str
    session_id: str

    # === 意图 & 分发 ===
    intent: QueryIntent
    use_sql: bool
    use_rag: bool

    # === SQL 工作流 ===
    generated_sql: Optional[str]
    sql_result: Optional[dict]
    sql_error: Optional[str]
    sql_is_valid: bool

    # === RAG 工作流 ===
    retrieved_docs: Optional[list]
    rag_result: Optional[str]

    # === Critic 反馈 ===
    critic_feedback: Optional[str]
    needs_regeneration: bool

    # === 记忆系统 ===
    session_history: Annotated[list[dict], add_messages]

    # === 工作流控制 ===
    current_step: WorkflowStep
    retry_count: int
    max_retries: int
    error: Optional[str]


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
        use_sql=False,
        use_rag=False,
        generated_sql=None,
        sql_result=None,
        sql_error=None,
        sql_is_valid=False,
        retrieved_docs=None,
        rag_result=None,
        critic_feedback=None,
        needs_regeneration=False,
        session_history=[],
        current_step=WorkflowStep.COORDINATOR,
        retry_count=0,
        max_retries=max_retries,
        error=None,
    )