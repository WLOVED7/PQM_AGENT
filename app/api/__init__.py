"""
API模块
"""
from fastapi import APIRouter

from app.api.agent import router as agent_router
from app.api.documents import router as documents_router
from app.api.monitor import router as monitor_router
from app.api.upload import router as upload_router

api_router = APIRouter()

api_router.include_router(agent_router)
api_router.include_router(documents_router)
api_router.include_router(monitor_router)
api_router.include_router(upload_router)

__all__ = ["api_router"]