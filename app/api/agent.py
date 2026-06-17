"""
=============================================================================
Agent API 路由 (api/agent.py)
=============================================================================

【用途】
提供 Agent 查询接口，基于 LangGraph 多 Agent 系统。

【接口】
POST /api/v1/agent/query - 执行自然语言查询（多 Agent 协作）
POST /api/v1/agent/cancel/{session_id} - 中断正在运行的查询
POST /api/v1/agent/resume/{session_id} - 从最近 checkpoint 继续未完成的查询
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
import asyncio

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any

from app.core.pqm_graph import run_pqm_graph, pqm_graph
from app.memory.short_term_memory import session_memory
from app.api.monitor import increment_query_count
from app.utils.logger import get_logger

logger = get_logger(__name__)


router = APIRouter(prefix="/agent", tags=["Agent"])


# 同一 session 同时只能有一个运行中的 graph 任务
_running_tasks: Dict[str, asyncio.Task] = {}


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
    pdf_urls: Optional[List[str]] = Field(default=None, description="相关 SIP PDF 文件 URL 列表")
    cancelled: bool = False


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
# 内部工具
# =============================================================================
def _build_response(result: Dict[str, Any], session_id: str, question: str) -> QueryResponse:
    """从 graph 最终 state 构建 QueryResponse"""
    sql_domain = result.get("sql", {})
    result_domain = result.get("result", {})
    sql_result = sql_domain.get("sql_result")
    sql_error = sql_domain.get("sql_error")
    success = sql_result.get("success", False) if sql_result else False

    return QueryResponse(
        success=success,
        question=result.get("question", question),
        session_id=result.get("session_id", session_id),
        intent=result.get("intent", "unknown"),
        sql=sql_domain.get("generated_sql"),
        data=sql_result.get("data") if sql_result else None,
        count=sql_result.get("count", 0) if sql_result else 0,
        error=sql_error,
        answer=result_domain.get("final_response") or _build_answer(result),
        pdf_urls=sql_result.get("pdf_urls", []) if sql_result else [],
    )


def _cancelled_response(session_id: str, question: str) -> QueryResponse:
    """构造被取消的响应"""
    return QueryResponse(
        success=False,
        question=question,
        session_id=session_id,
        intent="unknown",
        answer="（已停止）",
        cancelled=True,
    )


async def _cancel_existing_task(session_id: str) -> None:
    """如果该 session 有正在运行的任务，取消并等待其结束。"""
    existing = _running_tasks.get(session_id)
    if existing is None or existing.done():
        return
    logger.info(f"Cancelling existing task for session {session_id}")
    existing.cancel()
    try:
        await existing
    except (asyncio.CancelledError, Exception):
        pass


async def _run_with_registry(session_id: str, coro):
    """把 coroutine 包成 task 注册到 registry，等待并清理。"""
    task = asyncio.create_task(coro)
    _running_tasks[session_id] = task
    try:
        return await task
    finally:
        # 仅当 registry 里仍指向我们这个 task 时才清理（防止后续任务被误清）
        if _running_tasks.get(session_id) is task:
            _running_tasks.pop(session_id, None)


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
    """
    # 如果同 session 有遗留任务，先取消
    await _cancel_existing_task(request.session_id)

    try:
        result = await _run_with_registry(
            request.session_id,
            run_pqm_graph(question=request.question, session_id=request.session_id),
        )
        increment_query_count()
        return _build_response(result, request.session_id, request.question)
    except asyncio.CancelledError:
        logger.info(f"Query cancelled for session {request.session_id}")
        return _cancelled_response(request.session_id, request.question)
    except Exception as e:
        import traceback
        logger.error(f"Agent query failed: {e}")
        logger.debug(f"Traceback: {traceback.format_exc()}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/cancel/{session_id}")
async def cancel_query(session_id: str):
    """中断该 session 正在运行的查询。已完成的节点 state 会保留在 checkpoint 中。"""
    task = _running_tasks.get(session_id)
    if task is None or task.done():
        return {"cancelled": False, "reason": "no running task"}
    task.cancel()
    logger.info(f"Cancel requested for session {session_id}")
    return {"cancelled": True}


@router.post("/resume/{session_id}", response_model=QueryResponse)
async def resume_query(session_id: str):
    """从最近的 checkpoint 继续上一次被中断的查询。"""
    # 防止并发：如果还有任务在跑，先取消
    await _cancel_existing_task(session_id)

    config = {"configurable": {"thread_id": session_id}}

    async def _resume():
        # 传 None 告诉 LangGraph 从 checkpoint 继续，而不是用新 state 重置
        return await pqm_graph.ainvoke(None, config=config)

    try:
        result = await _run_with_registry(session_id, _resume())
    except asyncio.CancelledError:
        logger.info(f"Resume cancelled for session {session_id}")
        return _cancelled_response(session_id, "")
    except Exception as e:
        import traceback
        logger.error(f"Resume failed: {e}")
        logger.debug(f"Traceback: {traceback.format_exc()}")
        raise HTTPException(status_code=500, detail=str(e))

    question = result.get("question", "") if isinstance(result, dict) else ""
    return _build_response(result, session_id, question)


def _build_answer(result: Dict[str, Any]) -> str:
    """构建最终回复文本（用于 final_response 未生成时的兜底）"""
    sql_domain = result.get("sql", {})
    rag_domain = result.get("rag", {})
    sql_result = sql_domain.get("sql_result")
    sql_error = sql_domain.get("sql_error")
    rag_result = rag_domain.get("answer")

    if sql_result and sql_result.get("success"):
        data = sql_result.get("data", [])
        count = sql_result.get("count", 0)

        if count == 0:
            return "没有找到符合条件的数据。"

        lines = [f"找到 {count} 条结果：\n"]
        for i, row in enumerate(data[:10], 1):
            lines.append(f"{i}. {repr(row)}")

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
    """获取对话历史"""
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
    """清除会话历史"""
    session_memory.clear_session(session_id)
    return {"message": f"Session {session_id} 已清除"}


@router.get("/health", response_model=HealthResponse)
async def health_check():
    """检查 Agent 服务状态"""
    from app.core import pqm_graph as _graph_module

    return HealthResponse(
        status="healthy",
        graph_ready=_graph_module is not None,
        memory_sessions=len(session_memory.list_sessions()),
    )
