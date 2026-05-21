"""
=============================================================================
Agent API 路由 (api/agent.py)
=============================================================================

【用途】
提供 Agent 查询接口，基于 LangGraph 多 Agent 系统。

【接口】
POST /api/v1/agent/query - 执行自然语言查询（多 Agent 协作）
GET  /api/v1/agent/health - 检查 Agent 服务状态
GET  /api/v1/agent/history - 获取对话历史
DELETE /api/v1/agent/history - 清除会话历史

【多 Agent 架构】
Coordinator (意图识别) → SQL Agent / RAG Agent
                         ↓
                    Critic Agent (审查)
                         ↓
                    SQL Executor
                         ↓
                    Result Aggregation
"""
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any

from app.core.pqm_graph import run_pqm_graph
from app.memory.short_term_memory import session_memory


router = APIRouter(prefix="/agent", tags=["Agent"])


# =============================================================================
# 请求/响应模型
# =============================================================================
class QueryRequest(BaseModel):
    """查询请求"""
    question: str = Field(..., description="用户问题")
    session_id: str = Field(default="default", description="Session ID，用于记忆管理")
    mode: str = Field(default="auto", description="模式: auto=自动识别, sql=仅SQL, rag=仅RAG")


class QueryResponse(BaseModel):
    """查询响应"""
    success: bool
    question: str
    session_id: str
    intent: str
    sql: Optional[str] = None
    data: Optional[List[Dict[str, Any]]] = None
    count: int = 0
    error: Optional[str] = None
    answer: Optional[str] = None


class HistoryResponse(BaseModel):
    """历史记录响应"""
    session_id: str
    history: List[Dict[str, Any]]
    turn_count: int


class HealthResponse(BaseModel):
    """健康检查响应"""
    status: str
    graph_ready: bool
    memory_sessions: int


# =============================================================================
# API 端点
# =============================================================================
@router.post("/query", response_model=QueryResponse)
async def query(request: QueryRequest):
    """
    执行自然语言查询（多 Agent 协作）

    【工作流程】
    1. Coordinator 意图识别
    2. SQL Agent / RAG Agent 执行
    3. Critic Agent 审查（可选）
    4. Result Aggregation 汇总

    Args:
        request: QueryRequest，包含用户问题和 session_id

    Returns:
        QueryResponse，查询结果
    """
    try:
        # 运行 LangGraph 多 Agent 系统
        result = await run_pqm_graph(
            question=request.question,
            session_id=request.session_id,
        )

        # 提取结果
        sql_result = result.get("sql_result")
        sql_error = result.get("sql_error")

        # 构建回复
        success = sql_result.get("success", False) if sql_result else False

        return QueryResponse(
            success=success,
            question=result["question"],
            session_id=result["session_id"],
            intent=result.get("intent", "unknown"),
            sql=result.get("generated_sql"),
            data=sql_result.get("data") if sql_result else None,
            count=sql_result.get("count", 0) if sql_result else 0,
            error=sql_error,
            answer=result.get("final_response") or _build_answer(result),
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


def _build_answer(result: Dict[str, Any]) -> str:
    """构建最终回复文本"""
    sql_result = result.get("sql_result")
    sql_error = result.get("sql_error")
    rag_result = result.get("rag_result")

    if sql_result and sql_result.get("success"):
        data = sql_result.get("data", [])
        count = sql_result.get("count", 0)

        if count == 0:
            return "没有找到符合条件的数据。"

        lines = [f"找到 {count} 条结果：\n"]
        for i, row in enumerate(data[:10], 1):
            lines.append(f"{i}. {row}")

        if count > 10:
            lines.append(f"\n... 还有 {count - 10} 条结果未显示")

        return "\n".join(lines)

    if sql_error:
        if rag_result and rag_result != "RAG 功能待完善":
            return f"数据库查询失败：{sql_error}\n\n另外，关于您的问题：\n{rag_result}"
        return f"抱歉，无法回答您的问题。数据库查询失败：{sql_error}"

    if rag_result and rag_result != "RAG 功能待完善":
        return rag_result

    return "抱歉，无法回答您的问题。"


@router.get("/history/{session_id}", response_model=HistoryResponse)
async def get_history(session_id: str, limit: int = 10):
    """
    获取对话历史

    Args:
        session_id: Session ID
        limit: 返回最近 N 条消息

    Returns:
        HistoryResponse，对话历史
    """
    history = session_memory.get_history(session_id, limit=limit * 2)
    session_info = session_memory.get_session_info(session_id)
    turn_count = session_info.get("turn_count", 0) if session_info else 0

    return HistoryResponse(
        session_id=session_id,
        history=history,
        turn_count=turn_count,
    )


@router.delete("/history/{session_id}")
async def clear_history(session_id: str):
    """
    清除会话历史

    Args:
        session_id: Session ID

    Returns:
        成功消息
    """
    session_memory.clear_session(session_id)
    return {"message": f"Session {session_id} 已清除"}


@router.get("/health", response_model=HealthResponse)
async def health_check():
    """
    检查 Agent 服务状态

    Returns:
        HealthResponse，服务状态
    """
    from app.core import pqm_graph

    return HealthResponse(
        status="healthy",
        graph_ready=pqm_graph is not None,
        memory_sessions=len(session_memory.list_sessions()),
    )