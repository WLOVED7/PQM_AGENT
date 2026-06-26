"""
=============================================================================
热压品质异常预测系统 (PQM - Press Quality Monitor)
=============================================================================

系统用途：
--------
1. 【Text2SQL】Agent 用自然语言查询 sip_records 检验数据
2. 【RAG 检索】支持向量化和全文搜索

技术架构：
--------
FastAPI (异步API)
    ↓
asyncpg (直连，不使用 ORM)
    ↓
PostgreSQL (数据库)
    ↓
Pydantic (数据验证)

数据库表：
--------
sip_records        - SIP 检验记录扁平表（单表）
"""
import asyncio
import time
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from app.core.config import settings
from app.api import api_router
from app.api.nap import nap_router
from app.db.connection import init_db, close_db
from app.utils.logger import get_logger

_logger = get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """应用生命周期管理"""
    await init_db()

    # 预热 LLM：触发包导入 + 建立 TCP/TLS 连接，消除首次请求冷启动延迟
    try:
        from langchain_core.messages import HumanMessage
        from app.agents.base.llm import create_chat_llm
        _logger.info("正在预热 LLM 连接...")
        llm = create_chat_llm()
        await asyncio.to_thread(llm.invoke, [HumanMessage(content=".")])
        _logger.info("LLM 预热完成")
    except Exception as e:
        _logger.warning(f"LLM 预热失败（不影响启动）: {e}")

    yield
    await close_db()


app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    description="""
    质量检验知识库 API

    ## 功能
    - Text2SQL 自然语言查询
    - 支持向量化和全文搜索（RAG）

    ## 技术栈
    - FastAPI
    - aiomysql (直连)
    - MySQL 8
    - LangChain LLM
    """,
    openapi_url=f"{settings.API_PREFIX}/openapi.json",
    docs_url=f"{settings.API_PREFIX}/docs",
    redoc_url=f"{settings.API_PREFIX}/redoc",
    lifespan=lifespan,
)

# CORS配置
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 注册路由
app.include_router(api_router, prefix=settings.API_PREFIX)
app.include_router(nap_router)  # NAP 协议接口：/meta /stream（无前缀，根级别）

# 挂载 SIP 文件目录（确保目录存在后挂载，不依赖启动时是否已有文件）
DOCUMENTS_DIR = Path(__file__).parent.parent / "documents"
DOCUMENTS_DIR.mkdir(exist_ok=True)
app.mount("/documents", StaticFiles(directory=str(DOCUMENTS_DIR)), name="documents")


@app.get("/", tags=["健康检查"])
async def root():
    """根路径"""
    return {
        "name": settings.APP_NAME,
        "version": settings.APP_VERSION,
        "status": "running",
    }


@app.get("/health", tags=["健康检查"])
async def health_check():
    """健康检查 — NAP 协议要求 status 必须为 'ok'"""
    return {"status": "ok", "timestamp": int(time.time())}


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=8000,
        reload=settings.DEBUG,
    )