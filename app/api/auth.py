"""
管理员登录接口
POST /api/v1/auth/login  —  验证用户名/密码，返回 JWT access_token
"""
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from app.core.auth import create_access_token
from app.core.config import settings

router = APIRouter(prefix="/auth", tags=["Auth"])


class LoginRequest(BaseModel):
    username: str
    password: str


@router.post("/login")
async def login(body: LoginRequest):
    if body.username != settings.ADMIN_USERNAME or body.password != settings.ADMIN_PASSWORD:
        raise HTTPException(status_code=401, detail="用户名或密码错误")
    token = create_access_token()
    return {"access_token": token, "token_type": "bearer"}
