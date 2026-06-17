from fastapi import APIRouter
from app.memory.short_term_memory import session_memory
from app.tools.ragflow_client import get_ragflow_client

router = APIRouter(prefix="/monitor", tags=["Monitor"])

# 累计查询计数（进程内）
_query_count = 0


def increment_query_count():
    global _query_count
    _query_count += 1


@router.get("/stats")
async def get_stats():
    """返回系统统计数据"""
    sessions = session_memory.list_sessions()
    # 文档数从 RagFlow 取
    doc_count = 0
    try:
        client = get_ragflow_client()
        resp = await client.client.get(
            f"/api/v1/datasets/{client.default_dataset_id}/documents",
            params={"page": 1, "page_size": 1},
        )
        data = resp.json()
        inner = data.get("data", {})
        if isinstance(inner, dict):
            doc_count = inner.get("total", 0)
    except Exception:
        pass

    return {
        "queries": _query_count,
        "sessions": len(sessions),
        "documents": doc_count,
    }


@router.get("/recent")
async def get_recent():
    """返回所有 session 的最近用户问题（最多 20 条）"""
    recent = []
    for sid in session_memory.list_sessions():
        history = session_memory.get_history(sid, limit=20)
        for msg in history:
            if msg["role"] == "user":
                recent.append({
                    "session": sid,
                    "question": msg["content"],
                    "time": msg.get("timestamp", "")[:16].replace("T", " "),
                })
    # 按时间倒序，取最近 20 条
    recent.sort(key=lambda x: x["time"], reverse=True)
    return recent[:20]
