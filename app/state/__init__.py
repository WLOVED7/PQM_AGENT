"""
=============================================================================
State Module - 状态定义
=============================================================================
定义 LangGraph 多 Agent 系统的共享状态结构。
"""
from app.state.state import (
    QueryIntent,
    WorkflowStep,
    AgentState,
    create_initial_state,
)

__all__ = [
    "QueryIntent",
    "WorkflowStep",
    "AgentState",
    "create_initial_state",
]