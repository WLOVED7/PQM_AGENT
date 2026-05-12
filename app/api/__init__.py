"""
API模块
"""
from fastapi import APIRouter

from app.api.agent import router as agent_router

api_router = APIRouter()

api_router.include_router(agent_router)

__all__ = ["api_router"]