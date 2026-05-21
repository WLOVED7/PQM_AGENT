"""
=============================================================================
Session Memory - Session 级记忆系统 (memory/short_term_memory.py)
=============================================================================

【核心功能】
- 内存存储，Session 结束后自动清理
- 按 session_id 隔离
- 支持消息历史

【设计原则】
- 感知: 记录用户问题和系统响应
- 记忆: 存储对话历史供 LLM 上下文使用
- 执行: 提供 add_message, get_history, get_context_for_llm 接口
"""
from typing import Dict, List, Optional
from datetime import datetime
from collections import defaultdict


class SessionMemory:
    """
    Session 级记忆存储

    【特性】
    - 内存存储，Session 结束后自动清理
    - 按 session_id 隔离
    - 支持消息历史
    """

    def __init__(self):
        self._sessions: Dict[str, List[dict]] = defaultdict(list)
        self._metadata: Dict[str, dict] = defaultdict(dict)

    def create_session(self, session_id: str) -> None:
        """
        创建新 Session

        Args:
            session_id: Session ID
        """
        if session_id not in self._sessions:
            self._sessions[session_id] = []
            self._metadata[session_id] = {
                "created_at": datetime.now(),
                "last_active": datetime.now(),
                "turn_count": 0,
            }

    def add_message(self, session_id: str, role: str, content: str) -> None:
        """
        添加消息到 Session 历史

        Args:
            session_id: Session ID
            role: "user" | "assistant" | "system"
            content: 消息内容
        """
        self.create_session(session_id)

        self._sessions[session_id].append({
            "role": role,
            "content": content,
            "timestamp": datetime.now().isoformat(),
        })

        self._metadata[session_id]["last_active"] = datetime.now()
        self._metadata[session_id]["turn_count"] += 1

    def get_history(self, session_id: str, limit: int = 10) -> List[dict]:
        """
        获取 Session 历史

        Args:
            session_id: Session ID
            limit: 返回最近 N 条消息

        Returns:
            消息列表
        """
        if session_id not in self._sessions:
            return []

        messages = self._sessions[session_id]
        return messages[-limit:] if limit > 0 else messages

    def get_context_for_llm(self, session_id: str, limit: int = 5) -> str:
        """
        获取用于 LLM 的上下文字符串

        Args:
            session_id: Session ID
            limit: 包含最近 N 轮对话

        Returns:
            格式化的上下文字符串
        """
        history = self.get_history(session_id, limit=limit * 2)

        if not history:
            return ""

        lines = ["【对话历史】"]
        for msg in history:
            role_label = "用户" if msg["role"] == "user" else "助手"
            lines.append(f"{role_label}: {msg['content']}")

        return "\n".join(lines)

    def clear_session(self, session_id: str) -> None:
        """清除 Session"""
        if session_id in self._sessions:
            del self._sessions[session_id]
        if session_id in self._metadata:
            del self._metadata[session_id]

    def get_session_info(self, session_id: str) -> Optional[dict]:
        """获取 Session 信息"""
        return self._metadata.get(session_id)

    def list_sessions(self) -> List[str]:
        """列出所有活跃的 Session ID"""
        return list(self._sessions.keys())


# 全局单例
session_memory = SessionMemory()