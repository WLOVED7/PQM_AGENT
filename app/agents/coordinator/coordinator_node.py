"""
=============================================================================
Coordinator Agent - 意图识别与任务分发 (agents/coordinator/coordinator_node.py)
=============================================================================

【核心功能】
1. 感知: 理解用户问题
2. 理解: 意图识别 (DATABASE_QUERY / DOCUMENT_SEARCH / MIXED)
3. 执行: 决定后续工作流

【LLM 参与】
使用 LLM 而非关键词匹配来判断意图，体现真正的 Agent 感知能力。
"""
from typing import Literal

from langchain_core.messages import HumanMessage, SystemMessage

from app.agents.base.llm import create_chat_llm
from app.graph.state import AgentState, QueryIntent, WorkflowStep
from app.agents.memory.session_memory import session_memory


COORDINATOR_PROMPT = """你是 PQM 质量检验知识库的 Coordinator Agent。

【你的职责】
1. 理解用户问题
2. 判断用户意图：SQL查询 / RAG检索 / 混合
3. 决定后续工作流

【意图类型】
- DATABASE_QUERY: 需要数据库查询（默认）
  - 问"标准是什么"、"要求是什么"、"规范" → 数据库查询
  - 问"多少"、"哪些"、"找出"、"查询"、"统计"、"列表"、"有哪些"、"查一下"
  - 问"硬度"、"AQL"、"公差"、"材料"、"表面处理"等具体参数
  - 问"前横梁"、"车门"、"电池"等具体零件相关问题
- DOCUMENT_SEARCH: 需要知识库检索（仅通用概念）
  - 问"什么是AQL"、"什么是SPC"等概念解释
  - 问"检验流程"、"质量体系"等通用知识
- MIXED: 混合需求（既需要查询也需要检索）
- UNKNOWN: 无法判断（默认走 DATABASE_QUERY）

【判断标准】
1. 优先判断是否需要数据库查询（大多数质检问题都需要查数据库）
2. 只有明确问"什么是XXX"且是纯概念性知识时才走 RAG
3. 问"XX的标准是什么"、"XX的要求是什么" → DATABASE_QUERY
4. 问"XX的参数"、"XX的规格" → DATABASE_QUERY

【输出格式】
只输出以下 JSON 格式，不要其他内容：
{"intent": "database_query|document_search|mixed|unknown", "use_sql": true|false, "use_rag": true|false}"""


async def coordinator_node(state: AgentState) -> AgentState:
    """
    Coordinator Node - 意图识别与分发

    【感知】理解用户问题
    【理解】通过 LLM 判断意图
    【执行】设置 use_sql/use_rag 决定后续工作流

    Args:
        state: AgentState，包含 question 和 session_history

    Returns:
        更新后的 state，包含 intent, use_sql, use_rag
    """
    llm = create_chat_llm()
    question = state["question"]
    session_id = state["session_id"]

    # 获取对话历史上下文
    history_context = session_memory.get_context_for_llm(session_id, limit=3)

    # 构建消息
    messages = [
        SystemMessage(content=COORDINATOR_PROMPT),
    ]

    if history_context:
        messages.append(HumanMessage(content=f"【对话历史】\n{history_context}\n\n【当前问题】\n{question}"))
    else:
        messages.append(HumanMessage(content=f"用户问题: {question}"))

    # 调用 LLM 判断意图
    response = llm.invoke(messages)
    response_text = response.strip() if response else ""

    # 解析意图
    intent, use_sql, use_rag = _parse_intent_response(response_text)

    # 更新记忆 - 记录用户问题
    session_memory.add_message(session_id, "user", question)

    return {
        **state,
        "intent": intent,
        "use_sql": use_sql,
        "use_rag": use_rag,
        "current_step": WorkflowStep.COORDINATOR,
    }


def _parse_intent_response(response: str) -> tuple:
    """
    解析 LLM 返回的意图 JSON

    Args:
        response: LLM 返回的文本

    Returns:
        (intent, use_sql, use_rag)
    """
    intent = QueryIntent.UNKNOWN
    use_sql = False
    use_rag = False

    response_lower = response.lower()

    # 解析 intent
    if "mixed" in response_lower:
        intent = QueryIntent.MIXED
        use_sql = True
        use_rag = True
    elif "document_search" in response_lower and "mixed" not in response_lower:
        intent = QueryIntent.DOCUMENT_SEARCH
        use_rag = True
    elif "database_query" in response_lower:
        intent = QueryIntent.DATABASE_QUERY
        use_sql = True
    else:
        # 默认走 SQL 查询
        intent = QueryIntent.DATABASE_QUERY
        use_sql = True

    return intent, use_sql, use_rag