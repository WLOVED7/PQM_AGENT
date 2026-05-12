"""
=============================================================================
质量检验知识库 (PQM - Quality Inspection Knowledge Base)
=============================================================================

项目背景：
--------
制造业需要对产品进行质量检验，检验的标准文件叫做 SIP (Standard Inspection Procedure)。

系统用途：
--------
1. 【Text2SQL】Agent 用自然语言查询数据
2. 【RAG 检索】支持向量化和全文搜索

技术架构：
--------
FastAPI (异步API)
    ↓
aiomysql (直连，不使用 ORM)
    ↓
MySQL 8 (数据库)
    ↓
Pydantic (数据验证)

数据库表：
--------
documents          - 文档主表
inspection_items   - 检验项目表
document_changes   - 版本变更记录表
"""
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import settings
from app.api import api_router
from app.db.connection import init_db, close_db


@asynccontextmanager
async def lifespan(app: FastAPI):
    """应用生命周期管理"""
    # 启动时
    await init_db()
    yield
    # 关闭时
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
    """健康检查"""
    return {"status": "healthy"}


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=8000,
        reload=settings.DEBUG,
    )