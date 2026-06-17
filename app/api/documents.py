from fastapi import APIRouter
from app.tools.ragflow_client import get_ragflow_client

router = APIRouter(prefix="/documents", tags=["Documents"])


@router.get("")
async def list_documents():
    """列出 RagFlow 知识库中的文档"""
    client = get_ragflow_client()
    try:
        import httpx
        resp = await client.client.get(
            f"/api/v1/datasets/{client.default_dataset_id}/documents",
            params={"page": 1, "page_size": 100},
        )
        data = resp.json()
        docs = data.get("data", {})
        if isinstance(docs, dict):
            items = docs.get("docs", [])
        else:
            items = []
        return {"documents": items, "total": len(items)}
    except Exception as e:
        return {"documents": [], "total": 0, "error": str(e)}
