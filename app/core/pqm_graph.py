"""
=============================================================================
PQM LangGraph 主图 (core/pqm_graph.py)
=============================================================================

【核心功能】
定义 LangGraph 状态机，包含所有节点和边路由。

【节点】
- coordinator: 意图识别
- sql_generation: SQL 生成 (Agent)
- critic: SQL 审查
- sql_execution: SQL 执行 (Tool)
- rag_retrieval: RAG 检索
- result_aggregation: 结果汇总
- response_optimization: LLM 优化输出

【边路由逻辑】
- coordinator → sql_generation (use_sql=True)
- coordinator → rag_retrieval (use_rag=True & not use_sql)
- coordinator → result_aggregation (unknown intent)
- sql_generation → critic
- critic → sql_execution (sql_valid=True)
- critic → sql_generation (needs_regeneration & retry_count < max)
- critic → result_aggregation (retry exhausted)
- sql_execution → result_aggregation
- rag_retrieval → result_aggregation
- result_aggregation → response_optimization
- response_optimization → END

【Critic 重试循环】
                    ┌─────────────────┐
                    │ sql_generation  │ (Agent)
                    └────────┬────────┘
                             │
                    ┌────────▼────────┐
                    │     critic      │
                    └────────┬────────┘
                             │
              ┌──────────────┴──────────────┐
              │                             │
        sql_valid=True          needs_regeneration=True
              │                             │
              ▼                             ▼
    ┌─────────────────┐      ┌─────────────────────────┐
    │ sql_execution   │      │ retry_count < max_retries│
    │   (Tool)        │      └────────────┬──────────────┘
    └────────┬────────┘                   │
             │                   ┌─────────┴─────────┐
             │                   │                   │
             │                  Yes                   No
             │                   │                   │
             ▼                   ▼                   ▼
    ┌─────────────────┐  ┌─────────────────┐  ┌─────────────────────┐
    │result_aggregation│  │sql_generation   │  │result_aggregation  │
    └─────────────────┘  │(retry + 1)     │  │  (return error)     │
                         └─────────────────┘  └─────────────────────┘

【检查点 (Checkpoint)】
当前版本 (langgraph 1.1.10) 使用 MemorySaver 内存存储。
后续升级到 langgraph >= 1.3.0 后可切换到 SqliteSaver 持久化存储。
"""
from langgraph.graph import StateGraph, END
from langgraph.checkpoint.memory import MemorySaver

from app.state.state import AgentState, WorkflowStep
from app.agents.coordinator.coordinator_node import coordinator_node
from app.agents.sql.sql_generation_node import sql_generation_node
from app.agents.sql.sql_execution_node import sql_execution_node
from app.agents.critic.critic_node import critic_node
from app.agents.rag.rag_retrieval_node import rag_retrieval_node
from app.agents.result.result_aggregation_node import result_aggregation_node
from app.agents.result.response_optimization_node import response_optimization_node
from app.utils.logger import get_logger

import functools
import json


# ===== 节点 IO 日志 =====
_io_logger = get_logger("app.graph.io")

# 节点返回的 state 中，仅这些键会被记录（避免打印巨大的全量 state）
_LOG_KEYS = ("intent", "current_step", "sql", "rag", "validation", "result", "global_context", "retry_exhausted", "error")


def _truncate(s: str, n: int = 1000) -> str:
    return s if len(s) <= n else s[:n] + f"... (截断, 共 {len(s)} 字符)"


def with_io_logging(name: str, fn):
    """包装 node 函数，在退出时记录节点输出到 app.graph.io logger。"""
    @functools.wraps(fn)
    async def wrapped(state):
        try:
            result = await fn(state)
        except Exception:
            _io_logger.exception(f"[{name}] ✖ EXCEPTION")
            raise
        delta = {k: result[k] for k in _LOG_KEYS if k in result}
        try:
            payload = json.dumps(delta, ensure_ascii=False, default=str)
        except (TypeError, ValueError):
            payload = repr(delta)
        _io_logger.info(f"[{name}] ◀ OUTPUT {_truncate(payload)}")
        return result
    return wrapped


# ===== 检查点存储 =====
_checkpointer = None


def get_checkpointer() -> MemorySaver:
    """获取或创建检查点存储（内存模式）"""
    global _checkpointer
    if _checkpointer is None:
        _checkpointer = MemorySaver()
    return _checkpointer


def create_pqm_graph(checkpointer: MemorySaver = None) -> StateGraph:
    """
    创建 PQM LangGraph

    节点:
    - coordinator: 意图识别
    - sql_generation: SQL 生成 (Agent)
    - critic: SQL 审查
    - sql_execution: SQL 执行 (Tool)
    - rag_retrieval: RAG 检索
    - result_aggregation: 结果汇总

    Returns:
        编译后的 StateGraph
    """
    # 创建图
    graph = StateGraph(AgentState)

    # ===== 注册节点 =====
    graph.add_node("coordinator", with_io_logging("coordinator", coordinator_node))
    graph.add_node("sql_generation", with_io_logging("sql_generation", sql_generation_node))
    graph.add_node("critic", with_io_logging("critic", critic_node))
    graph.add_node("sql_execution", with_io_logging("sql_execution", sql_execution_node))
    graph.add_node("rag_retrieval", with_io_logging("rag_retrieval", rag_retrieval_node))
    graph.add_node("result_aggregation", with_io_logging("result_aggregation", result_aggregation_node))
    graph.add_node("response_optimization", with_io_logging("response_optimization", response_optimization_node))

    # ===== 设置入口点 =====
    graph.set_entry_point("coordinator")

    # ===== 定义边路由函数 =====

    def route_after_coordinator(state: AgentState) -> str:
        """Coordinator 之后的路由"""
        global_context = state.get("global_context", {})
        use_sql = global_context.get("use_sql", False)
        use_rag = global_context.get("use_rag", False)

        if use_sql and use_rag:
            # MIXED 模式: 先走 SQL 路径（简化处理）
            return "sql_generation"
        elif use_sql:
            return "sql_generation"
        elif use_rag:
            return "rag_retrieval"
        else:
            return "result_aggregation"

    def route_after_critic(state: AgentState) -> str:
        """Critic 之后的路由"""
        validation_domain = state.get("validation", {})
        sql_domain = state.get("sql", {})
        sql_valid = validation_domain.get("sql_valid", False)
        retry_count = sql_domain.get("retry_count", 0)
        max_retries = state.get("max_retries", 2)

        if sql_valid:
            return "sql_execution"
        elif not sql_valid:
            # 需要重试
            if retry_count < max_retries:
                return "sql_generation"  # 重新生成
            else:
                # 重试耗尽，标记并返回错误
                state["retry_exhausted"] = True
                return "result_aggregation"  # 放弃
        else:
            return "result_aggregation"

    # ===== 注册边 =====

    # Coordinator → 其他节点
    graph.add_conditional_edges(
        "coordinator",
        route_after_coordinator,
        {
            "sql_generation": "sql_generation",
            "rag_retrieval": "rag_retrieval",
            "result_aggregation": "result_aggregation",
        }
    )

    # SQL 流程: sql_generation → critic → sql_execution → result_aggregation
    graph.add_edge("sql_generation", "critic")

    graph.add_conditional_edges(
        "critic",
        route_after_critic,
        {
            "sql_execution": "sql_execution",
            "sql_generation": "sql_generation",
            "result_aggregation": "result_aggregation",
        }
    )

    graph.add_edge("sql_execution", "result_aggregation")

    # RAG 流程
    graph.add_edge("rag_retrieval", "result_aggregation")

    # 结束
    graph.add_edge("result_aggregation", "response_optimization")

    # 结束
    graph.add_edge("response_optimization", END)

    # 使用检查点（如果提供）
    if checkpointer:
        return graph.compile(checkpointer=checkpointer)
    return graph.compile()


# ===== 全局图实例 =====
pqm_graph = create_pqm_graph(get_checkpointer())


async def run_pqm_graph_stream(question: str, session_id: str):
    """
    运行 PQM Graph (流式版本)

    Args:
        question: 用户问题
        session_id: Session ID (用作 checkpoint thread_id)

    Yields:
        每个节点的输出
    """
    from app.state.state import create_initial_state

    initial_state = create_initial_state(
        question=question,
        session_id=session_id,
        max_retries=2,
    )

    config = {"configurable": {"thread_id": session_id}}

    async for chunk in pqm_graph.astream(initial_state, config=config, stream_mode="updates"):
        yield chunk


async def run_pqm_graph(question: str, session_id: str) -> AgentState:
    """
    运行 PQM Graph

    Args:
        question: 用户问题
        session_id: Session ID (用作 checkpoint thread_id)

    Returns:
        最终状态
    """
    from app.state.state import create_initial_state

    initial_state = create_initial_state(
        question=question,
        session_id=session_id,
        max_retries=2,
    )

    config = {"configurable": {"thread_id": session_id}}
    result = await pqm_graph.ainvoke(initial_state, config=config)
    return result