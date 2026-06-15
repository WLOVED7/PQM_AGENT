"""
=============================================================================
RagFlow 客户端工具 (tools/ragflow_client.py)
=============================================================================

【功能】
封装 RagFlow API，支持文档检索和问答。
使用 @tool 装饰器，符合 LangGraph 规范。

【配置】
配置在 .env 文件中：
RAGFLOW_BASE_URL
RAGFLOW_API_KEY
RAGFLOW_DATASET_ID
"""
import os
import httpx
from typing import Optional, List, Dict, Any

from langchain_core.tools import tool
from app.utils.logger import get_logger

logger = get_logger(__name__)


class RagFlowClient:
    """RagFlow API 客户端"""

    def __init__(
        self,
        base_url: Optional[str] = None,
        api_key: Optional[str] = None,
        timeout: int = 60,
    ):
        self.base_url = base_url or os.getenv("RAGFLOW_BASE_URL", "")
        self.api_key = api_key or os.getenv("RAGFLOW_API_KEY", "")
        self.timeout = timeout
        self.default_dataset_id = os.getenv("RAGFLOW_DATASET_ID", "")

        self.client = httpx.AsyncClient(
            base_url=self.base_url,
            timeout=timeout,
            headers={
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json",
            },
        )

    async def close(self):
        await self.client.aclose()

    async def list_datasets(self) -> List[Dict]:
        try:
            response = await self.client.get("/api/v1/datasets")
            response.raise_for_status()
            data = response.json()
            return data.get("data", [])
        except Exception as e:
            logger.error(f"获取数据集列表失败: {e}")
            return []

    async def retrieval(
        self,
        query: str,
        dataset_id: Optional[str] = None,
        top_k: int = 5,
    ) -> Dict[str, Any]:
        """
        从数据集检索 chunks

        Args:
            query: 查询文本
            dataset_id: 数据集 ID（可选，默认使用配置中的数据集）
            top_k: 返回结果数量

        Returns:
            检索结果，包含 chunks 和 answer
        """
        try:
            payload = {
                "question": query,
                "top_k": top_k,
                "highlight": True,
            }

            ds_id = dataset_id or self.default_dataset_id
            payload["dataset_ids"] = [ds_id]

            response = await self.client.post("/api/v1/retrieval", json=payload)
            response.raise_for_status()
            resp = response.json()

            if resp.get("code") != 0:
                logger.error(f"RagFlow 检索错误: code={resp.get('code')} {resp.get('message')}")
                return {"error": resp.get("message", "unknown error"), "chunks": [], "answer": ""}

            result = resp.get("data", {}) if isinstance(resp.get("data"), dict) else {}
            logger.info(f"RagFlow 检索完成，问题: {query[:50]}..., 结果数: {len(result.get('chunks', []))}")
            return result

        except httpx.HTTPStatusError as e:
            logger.error(f"RagFlow HTTP 错误: {e.response.status_code}")
            return {"error": f"HTTP {e.response.status_code}", "chunks": [], "answer": ""}
        except Exception as e:
            logger.error(f"RagFlow 检索失败: {e}")
            return {"error": str(e), "chunks": [], "answer": ""}


# 全局客户端实例
rag_client: Optional[RagFlowClient] = None


def get_ragflow_client() -> RagFlowClient:
    global rag_client
    if rag_client is None:
        rag_client = RagFlowClient()
    return rag_client


@tool
def rag_tool(question: str) -> str:
    """
    使用 RagFlow 知识库检索相关文档片段和生成答案。

    Args:
        question: 要检索的问题，例如 "前横梁硬度标准是什么？"

    Returns:
        包含检索文档片段和生成答案的字符串
    """
    import asyncio

    client = get_ragflow_client()

    try:
        loop = asyncio.get_event_loop()
    except RuntimeError:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)

    result = loop.run_until_complete(client.retrieval(query=question, top_k=5))

    if result.get("error"):
        return f"检索失败: {result['error']}"

    chunks = result.get("chunks", [])
    answer = result.get("answer", "")

    if not chunks and not answer:
        return "未找到相关文档"

    output = []
    if answer:
        output.append(f"【答案】\n{answer}")

    if chunks:
        output.append(f"\n【相关文档片段】（共 {len(chunks)} 条）")
        for i, chunk in enumerate(chunks[:3], 1):
            content = chunk.get("content", "")
            source = chunk.get("source", "")
            output.append(f"\n{i}. {content[:200]}...")
            if source:
                output.append(f"   来源: {source}")

    return "\n".join(output)