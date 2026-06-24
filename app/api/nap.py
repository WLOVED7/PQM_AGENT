"""
NoDeskClaw Agent Protocol (NAP) v1.0 接入层

实现平台要求的三个根级别接口：
  GET  /health  — 已在 main.py 处理，此处不重复
  GET  /meta    — Agent 元数据
  POST /stream  — NAP 格式 SSE 流式聊天
"""
import asyncio
import json
from typing import Any, Dict, List, Optional

from fastapi import APIRouter
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from app.core.config import settings
from app.core.pqm_graph import run_pqm_graph
from app.utils.logger import get_logger

logger = get_logger(__name__)

nap_router = APIRouter(tags=["NAP"])

_CHUNK_SIZE = 20  # 每次推送的字符数


# =============================================================================
# 请求体模型
# =============================================================================
class NAPMessage(BaseModel):
    role: str
    content: str


class NAPStreamRequest(BaseModel):
    protocol_version: str = "1.0"
    request_id: str
    session_id: str
    user_id: str
    organization_id: Optional[str] = None
    messages: List[NAPMessage]
    metadata: Optional[Dict[str, Any]] = None


# =============================================================================
# /meta
# =============================================================================
@nap_router.get("/meta")
async def nap_meta():
    """返回 Agent 元数据，平台 Sync 时调用"""
    return {
        "protocol_version": "1.0",
        "agent_id": "pqm-agent",
        "name": settings.APP_NAME,
        "description": "SIP 检验数据查询 Agent，支持自然语言 Text2SQL 和 RAG 知识库检索",
        "version": settings.APP_VERSION,
        "runtime": "langgraph",
        "capabilities": ["SIP检验数据查询", "Text2SQL", "知识库检索", "品质异常分析"],
    }


# =============================================================================
# /stream
# =============================================================================
@nap_router.post("/stream")
async def nap_stream(request: NAPStreamRequest):
    """NAP 流式聊天接口（SSE）"""

    # 取最后一条 user 消息作为本轮问题
    question = ""
    for msg in reversed(request.messages):
        if msg.role == "user":
            question = msg.content
            break

    if not question:
        async def _invalid():
            payload = json.dumps(
                {"code": "INVALID_REQUEST", "message": "请求中没有用户消息"},
                ensure_ascii=False,
            )
            yield f"event: error\ndata: {payload}\n\n"

        return StreamingResponse(_invalid(), media_type="text/event-stream")

    async def generate():
        try:
            result = await run_pqm_graph(
                question=question,
                session_id=request.session_id,
            )
            answer = _extract_answer(result)

            # 分块推送，让平台逐步展示
            for i in range(0, len(answer), _CHUNK_SIZE):
                chunk = answer[i: i + _CHUNK_SIZE]
                yield f"event: message\ndata: {chunk}\n\n"
                await asyncio.sleep(0.02)

            yield "event: done\ndata: complete\n\n"

        except Exception as e:
            logger.error(f"NAP stream error: {e}")
            payload = json.dumps(
                {"code": "AGENT_ERROR", "message": str(e)},
                ensure_ascii=False,
            )
            yield f"event: error\ndata: {payload}\n\n"

    return StreamingResponse(
        generate(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


# =============================================================================
# 内部工具
# =============================================================================
def _extract_answer(result: Dict[str, Any]) -> str:
    """从 graph 最终 state 提取回复文本"""
    result_domain = result.get("result", {})
    answer = result_domain.get("final_response") or result_domain.get("raw_response")
    if answer:
        return answer

    sql_domain = result.get("sql", {})
    rag_domain = result.get("rag", {})
    sql_result = sql_domain.get("sql_result")
    sql_error = sql_domain.get("sql_error")
    rag_answer = rag_domain.get("answer")

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
        if rag_answer and rag_answer != "RAG 功能待完善":
            return f"数据库查询失败：{sql_error}\n\n另外，关于您的问题：\n{rag_answer}"
        return f"抱歉，无法回答您的问题。数据库查询失败：{sql_error}"

    if rag_answer and rag_answer != "RAG 功能待完善":
        return rag_answer

    return "抱歉，无法回答您的问题。"
