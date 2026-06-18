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
from app.state.state import AgentState, QueryIntent, WorkflowStep
from app.memory.short_term_memory import session_memory
from app.utils.logger import get_logger

logger = get_logger(__name__)


COORDINATOR_PROMPT = """你是 PQM 质量检验知识库的 Coordinator Agent。

【你的职责】
1. 理解用户问题
2. 判断用户意图：SQL查询 / RAG检索 / 元问题 / 混合 / 通用回答
3. 决定后续工作流

【四大方向判断】

一、SQL数据库查询方向 (use_sql=True)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
目标：查询 SIP 检验标准数据
层级关系：客户 → 零件 → 检查项(标准/方法/抽检频次)
关键特征：问"标准是什么"、"要求是什么"、"规范"、具体参数

典型问法：
- "[客户]的[零件]，[检查项]的标准/要求是什么？"
- 例：比亚迪的前横梁，外观检查的标准是什么？
- 例：特斯拉的电池包，密封性检验的方法和抽检频次？
- 问"多少"、"哪些"、"找出"、"查询"、"统计"、"列表"、"有哪些"
- 问"AQL"、"抽样"、"频次"、"硬度"、"公差"、"材料"等具体参数
- 问某个零件的检验项目清单

二、RAG知识库检索方向 (use_rag=True)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
目标：从知识库检索工序异常处理经验
关注点：缺陷/异常的发生原因和解决方法
关键特征：问"原因是什么"、"怎么解决"、"怎么办"

典型问法：
- "[工序]出现[缺陷]的原因和解决方法？"
- 例：热压工序外观出现暗裂的发生原因和解决方法？
- 例：喷涂工序出现气泡是什么原因？怎么解决？
- 问"为什么"、"发生原因"、"解决办法"、"异常处理"
- 问"外观缺陷"、"性能异常"、"尺寸问题"等

三、元问题方向 (intent=meta_history, use_sql=False, use_rag=False)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
目标：关于"对话本身"的问题，不需要查数据库也不需要检索知识库
关键特征：询问对话历史、之前问过什么、你刚才说了什么

典型问法：
- "我上一个问题是什么？"
- "我之前问了什么？"
- "你刚才说了什么？"
- "我们聊到哪了？"

四、通用回答方向 (intent=general_llm, use_sql=False, use_rag=False)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
目标：直接用 LLM 知识回答，不需要查数据库或知识库
关键特征：通用知识、概念解释、方法论、闲聊、与质检系统无关的一般性问题

典型问法：
- "什么是 AQL？"（解释概念，不查具体数据）
- "SIP 是什么意思？"
- "你好"、"谢谢"等闲聊
- "帮我分析一下这段文字…"
- 任何明显无法通过数据库或知识库回答的问题

【判断规则】
1. 问题是关于对话历史/上下文本身 → META_HISTORY (use_sql=false, use_rag=false)
2. 问题包含"原因"、"解决"、"异常"、"缺陷" → RAG
3. 问题包含具体客户/零件 + 检验项目(标准/方法/抽检) → SQL
4. 问题既涉及具体零件检验，又涉及异常处理 → MIXED
5. 通用知识/概念/闲聊，无需查库 → GENERAL_LLM
6. 无法判断时 → GENERAL_LLM（不要强行走 SQL）

【输出格式】
只输出以下 JSON 格式，不要其他内容：
{"intent": "database_query|document_search|mixed|meta_history|general_llm|unknown", "use_sql": true|false, "use_rag": true|false}"""


async def coordinator_node(state: AgentState) -> AgentState:
    """
    Coordinator Node - 意图识别与分发

    【感知】理解用户问题
    【理解】通过 LLM 判断意图
    【执行】设置 use_sql/use_rag 决定后续工作流

    Args:
        state: AgentState，包含 question 和 session_id

    Returns:
        更新后的 state，包含 intent, use_sql, use_rag
    """
    logger.info(f"Coordinator 开始处理问题: {state['question'][:50]}...")

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
    logger.debug("调用 LLM 进行意图识别...")
    response = llm.invoke(messages)
    response_text = response.strip() if response else ""
    logger.debug(f"LLM 意图识别结果: {response_text[:100]}")

    # 解析意图
    intent, use_sql, use_rag = _parse_intent_response(response_text)

    logger.info(f"意图解析完成: intent={intent}, use_sql={use_sql}, use_rag={use_rag}")
    if intent == QueryIntent.UNKNOWN:
        logger.warning("无法识别意图，已路由到通用 LLM 兜底")
    if intent == QueryIntent.GENERAL_LLM:
        logger.info("通用问题，走 LLM 直接回答")

    # 更新记忆 - 记录用户问题
    session_memory.add_message(session_id, "user", question)

    return {
        "intent": intent,
        "global_context": {
            "use_sql": use_sql,
            "use_rag": use_rag,
        },
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

    # 解析 intent — 元问题优先识别
    if "meta_history" in response_lower:
        intent = QueryIntent.META_HISTORY
        # use_sql 和 use_rag 都为 False，路由直接走 result_aggregation
    elif "mixed" in response_lower:
        intent = QueryIntent.MIXED
        use_sql = True
        use_rag = True
    elif "document_search" in response_lower and "mixed" not in response_lower:
        intent = QueryIntent.DOCUMENT_SEARCH
        use_rag = True
    elif "database_query" in response_lower:
        intent = QueryIntent.DATABASE_QUERY
        use_sql = True
    elif "general_llm" in response_lower:
        intent = QueryIntent.GENERAL_LLM
    else:
        # 无法识别时走通用 LLM 兜底，不强行走 SQL
        intent = QueryIntent.GENERAL_LLM

    return intent, use_sql, use_rag