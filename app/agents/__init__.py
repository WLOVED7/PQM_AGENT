"""
Agents Module - 多 Agent 系统架构

目录结构:
    agents/
    ├── base/              # 基础组件
    │   └── llm.py         # LLM 调用接口
    ├── coordinator/       # Coordinator Agent (意图识别)
    ├── sql/               # SQL Agent (生成 + 执行)
    ├── critic/            # Critic Agent (SQL 审查)
    ├── rag/               # RAG Agent (文档检索)
    ├── memory/            # Session 记忆系统
    └── result/            # 结果汇总

【多 Agent 架构说明】
- Coordinator: 意图识别，决定走 SQL 还是 RAG
- SQL Agent: 生成和执行 SQL 查询
- Critic: 审查 SQL 正确性，支持重试
- RAG: 文档检索（待完善）
- Memory: Session 级记忆存储

使用示例:
    from app.graph import run_pqm_graph
    result = await run_pqm_graph("前横梁硬度标准是多少？", session_id="user-001")

    from app.agents.memory import session_memory
    history = session_memory.get_history("user-001")
"""
from app.agents.base import BaseLLM, LLMConfig, get_llm

# 导入子模块
from app.agents.memory import session_memory, SessionMemory

__all__ = [
    # Base
    "BaseLLM",
    "LLMConfig",
    "get_llm",
    # Memory
    "SessionMemory",
    "session_memory",
]