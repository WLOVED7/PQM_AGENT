"""
Base LLM Module - 基于 LangChain 的 LLM 调用接口
"""
import os
from typing import Optional, Literal, Any

from langchain_anthropic import ChatAnthropic
from langchain_core.messages import HumanMessage, SystemMessage, AIMessage


class LLMConfig:
    """LLM 配置"""
    provider: Literal["anthropic"] = "anthropic"
    auth_token: str = os.getenv("ANTHROPIC_AUTH_TOKEN", "")
    base_url: str = os.getenv("ANTHROPIC_BASE_URL", "https://api.minimaxi.com/anthropic")
    model: str = os.getenv("ANTHROPIC_MODEL", "MiniMax-M2.7")
    max_tokens: int = 4096
    temperature: float = 0.7


class BaseLLM:
    """LLM 基础类 (基于 LangChain)"""

    def __init__(self, config: Optional[LLMConfig] = None):
        self.config = config or LLMConfig()
        self._llm: Optional[ChatAnthropic] = None

    @property
    def llm(self) -> ChatAnthropic:
        """懒加载 LLM 实例"""
        if self._llm is None:
            self._llm = ChatAnthropic(
                model=self.config.model,
                anthropic_api_key=self.config.auth_token,
                base_url=self.config.base_url,
                max_tokens=self.config.max_tokens,
                temperature=self.config.temperature,
            )
        return self._llm

    async def generate(
        self,
        system: str,
        user_message: str,
        max_tokens: Optional[int] = None,
        temperature: Optional[float] = None,
    ) -> str:
        """生成文本

        Args:
            system: 系统提示词
            user_message: 用户消息
            max_tokens: 最大 token 数
            temperature: 温度参数

        Returns:
            LLM 生成的文本
        """
        messages = [
            SystemMessage(content=system),
            HumanMessage(content=user_message)
        ]

        # 使用同步调用（LangChain ChatAnthropic 默认是同步的）
        response = self.llm.invoke(messages)
        return response.content

    async def generate_with_history(
        self,
        system: str,
        messages: list[dict],
        max_tokens: Optional[int] = None,
        temperature: Optional[float] = None,
    ) -> str:
        """带历史的生成

        Args:
            system: 系统提示词
            messages: 消息历史列表 [{"role": "user"/"assistant", "content": "..."}]
            max_tokens: 最大 token 数
            temperature: 温度参数

        Returns:
            LLM 生成的文本
        """
        langchain_messages = [SystemMessage(content=system)]

        for msg in messages:
            if msg["role"] == "user":
                langchain_messages.append(HumanMessage(content=msg["content"]))
            elif msg["role"] == "assistant":
                langchain_messages.append(AIMessage(content=msg["content"]))

        response = self.llm.invoke(langchain_messages)
        return response.content

    def invoke(self, messages: list[Any]) -> str:
        """直接调用 LLM（用于 LangGraph）"""
        response = self.llm.invoke(messages)
        return response.content


def get_llm(config: Optional[LLMConfig] = None) -> BaseLLM:
    """获取 LLM 实例"""
    return BaseLLM(config)


def create_chat_llm() -> ChatAnthropic:
    """创建 LangChain ChatAnthropic 实例（用于 LangGraph）"""
    config = LLMConfig()
    return ChatAnthropic(
        model=config.model,
        anthropic_api_key=config.auth_token,
        base_url=config.base_url,
        max_tokens=config.max_tokens,
        temperature=config.temperature,
    )