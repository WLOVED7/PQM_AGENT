"""
=============================================================================
PQM LangGraph 主图 (graph/pqm_graph.py)
=============================================================================

【核心功能】
定义 LangGraph 状态机，包含所有节点和边路由。

【节点】
- coordinator: 意图识别
- sql_generation: SQL 生成
- critic: SQL 审查
- sql_execution: SQL 执行
- rag_retrieval: RAG 检索
- result_aggregation: 结果汇总

【边路由逻辑】
- coordinator → sql_generation (use_sql=True)
- coordinator → rag_retrieval (use_rag=True & not use_sql)
- coordinator → result_aggregation (unknown intent)
- sql_generation → critic
- critic → sql_execution (sql_is_valid=True)
- critic → sql_generation (needs_regeneration & retry_count < max)
- critic → result_aggregation (needs_regeneration & retry exhausted)
- sql_execution → result_aggregation
- rag_retrieval → result_aggregation

【Critic 重试循环】
                    ┌─────────────────┐
                    │  sql_generation │
                    └────────┬────────┘
                             │
                    ┌────────▼────────┐
                    │     critic      │
                    └────────┬────────┘
                             │
              ┌──────────────┴──────────────┐
              │                             │
        sql_is_valid=True          needs_regeneration=True
              │                             │
              ▼                             │
    ┌─────────────────┐                    │
    │  sql_execution   │                    │
    └─────────────────┘                    │
                                           ▼
                               ┌─────────────────────────┐
                               │ retry_count < max_retries│
                               └────────────┬──────────────┘
                                           │
                              ┌────────────┴────────────┐
                              │                         │
                           Yes                          No
                              │                         │
                              ▼                         ▼
                    ┌─────────────────┐      ┌─────────────────────┐
                    │sql_generation   │      │  result_aggregation  │
                    │(retry + 1)      │      │  (return error)      │
                    └─────────────────┘      └─────────────────────┘
"""
from langgraph.graph import StateGraph, END

from app.graph.state import AgentState, WorkflowStep
from app.agents.coordinator.coordinator_node import coordinator_node
from app.agents.sql.sql_generation_node import sql_generation_node
from app.agents.sql.sql_execution_node import sql_execution_node
from app.agents.critic.critic_node import critic_node
from app.agents.rag.rag_retrieval_node import rag_retrieval_node
from app.agents.result.result_aggregation_node import result_aggregation_node


def create_pqm_graph() -> StateGraph:
    """
    创建 PQM LangGraph

    节点:
    - coordinator: 意图识别
    - sql_generation: SQL 生成
    - critic: SQL 审查
    - sql_execution: SQL 执行
    - rag_retrieval: RAG 检索
    - result_aggregation: 结果汇总

    Returns:
        编译后的 StateGraph
    """
    # 创建图
    graph = StateGraph(AgentState)

    # ===== 注册节点 =====
    graph.add_node("coordinator", coordinator_node)
    graph.add_node("sql_generation", sql_generation_node)
    graph.add_node("critic", critic_node)
    graph.add_node("sql_execution", sql_execution_node)
    graph.add_node("rag_retrieval", rag_retrieval_node)
    graph.add_node("result_aggregation", result_aggregation_node)

    # ===== 设置入口点 =====
    graph.set_entry_point("coordinator")

    # ===== 定义边路由函数 =====

    def route_after_coordinator(state: AgentState) -> str:
        """Coordinator 之后的路由"""
        if state["use_sql"] and state["use_rag"]:
            # MIXED 模式: 先走 SQL 路径（简化处理）
            return "sql_generation"
        elif state["use_sql"]:
            return "sql_generation"
        elif state["use_rag"]:
            return "rag_retrieval"
        else:
            return "result_aggregation"

    def route_after_sql_generation(state: AgentState) -> str:
        """SQL 生成之后的路由"""
        return "critic"

    def route_after_critic(state: AgentState) -> str:
        """Critic 之后的路由"""
        if state["sql_is_valid"]:
            return "sql_execution"
        elif state["needs_regeneration"]:
            # 检查重试次数
            if state["retry_count"] < state["max_retries"]:
                return "sql_generation"  # 重新生成
            else:
                return "result_aggregation"  # 放弃
        else:
            return "result_aggregation"

    def route_after_sql_execution(state: AgentState) -> str:
        """SQL 执行之后的路由"""
        return "result_aggregation"

    def route_after_rag(state: AgentState) -> str:
        """RAG 之后的路由"""
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

    # SQL 流程
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
    graph.add_edge("result_aggregation", END)

    return graph.compile()


# ===== 全局图实例 =====
pqm_graph = create_pqm_graph()


async def run_pqm_graph(question: str, session_id: str) -> AgentState:
    """
    运行 PQM Graph

    Args:
        question: 用户问题
        session_id: Session ID

    Returns:
        最终状态
    """
    from app.graph.state import create_initial_state

    initial_state = create_initial_state(
        question=question,
        session_id=session_id,
        max_retries=2,
    )

    result = await pqm_graph.ainvoke(initial_state)
    return result