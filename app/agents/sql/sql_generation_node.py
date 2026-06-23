"""
=============================================================================
SQL Generation Node (agents/sql/sql_generation_node.py)
=============================================================================

【核心功能】
将自然语言问题转换为 SQL 查询语句。

【职责】
作为 Agent 节点，负责生成 SQL，但不执行 SQL。

【工作流程】
question → LLM 生成 SQL → 返回 generated_sql

【感知/理解/执行】
- 感知: 接收 question, session 历史
- 理解: 结合 Schema 上下文理解查询需求
- 执行: 调用 LLM 生成 SELECT SQL
"""
from langchain_core.messages import HumanMessage, SystemMessage

from app.agents.base.llm import create_chat_llm
from app.state.state import AgentState, WorkflowStep
from app.tools.schema_loader import schema_loader
from app.memory.short_term_memory import session_memory
from app.utils.logger import get_logger

logger = get_logger(__name__)


# =============================================================================
# SQL 生成 Prompt
# =============================================================================
SQL_GENERATION_PROMPT = """你是热压品质异常预测系统的 SQL 生成专家。

【数据库 Schema】
{schema_context}

【字段同义词映射】
{synonym_context}

【重要规则】
1. 只生成 SELECT 语句，禁止生成 INSERT/UPDATE/DELETE/DROP
2. 只有一张表: sip_records，禁止使用其他表名，禁止使用 JOIN
3. 字段名必须与 Schema 中完全一致
4. 字符串值用单引号包裹，如: customer = '比亚迪'
5. specification、inspection_method、inspection_frequency 均为 TEXT 普通字段，直接用 LIKE 查询
6. LIMIT 默认 100，最大不超过 100
7. 每次查询必须在 SELECT 中包含 document_id 字段，用于拼接 PDF 链接
8. 当用户提到工序名称（来料、热压、镭射、落料等），必须加 WHERE process = '工序名'
   - "来料" / "来料检验" → process = '来料'
   - "热压" / "热压工序" → process = '热压'
   - "镭射"             → process = '镭射'
   - "落料"             → process = '落料'

【示例】
用户问题: 比亚迪前横梁的检查标准是什么？
SQL:
SELECT inspection_item, specification, inspection_method, inspection_frequency, document_id
FROM sip_records
WHERE customer = '比亚迪'
  AND part_name LIKE '%前横梁%'
LIMIT 100

用户问题: 比亚迪前横梁来料外观检测标准是什么？
SQL:
SELECT inspection_item, specification, inspection_method, inspection_frequency, document_id
FROM sip_records
WHERE customer = '比亚迪'
  AND part_name LIKE '%前横梁%'
  AND process = '来料'
  AND inspection_item LIKE '%外观%'
LIMIT 100

用户问题: 热压工序的检验项有哪些？
SQL:
SELECT inspection_item, specification, inspection_method, document_id
FROM sip_records
WHERE process = '热压'
LIMIT 100

用户问题: AQL是0.65的检验项有哪些？
SQL:
SELECT inspection_item, inspection_frequency, part_name, document_id
FROM sip_records
WHERE inspection_frequency LIKE '%0.65%'
LIMIT 100

用户问题: 前横梁的机械性能要求是什么？
SQL:
SELECT inspection_item, specification, inspection_method, document_id
FROM sip_records
WHERE part_name LIKE '%前横梁%'
  AND inspection_item LIKE '%机械性能%'
LIMIT 100
"""


async def sql_generation_node(state: AgentState) -> AgentState:
    """
    SQL 生成 Node (Agent)

    【感知】接收 question, session 历史
    【理解】结合 Schema 上下文理解查询需求
    【执行】调用 LLM 生成 SQL

    Args:
        state: AgentState

    Returns:
        更新后的 state，包含 generated_sql
    """
    logger.info(f"SQL Generation 开始处理问题: {state['question'][:50]}...")

    llm = create_chat_llm()
    question = state["question"]
    session_id = state["session_id"]

    # 获取对话历史上下文
    history_context = session_memory.get_context_for_llm(session_id, limit=3)

    # 构建 Schema 上下文
    schema_context = schema_loader.generate_schema_context()
    synonym_context = schema_loader.generate_synonym_context()

    # 构建 Prompt
    prompt = SQL_GENERATION_PROMPT.format(
        schema_context=schema_context,
        synonym_context=synonym_context,
    )

    # 构建消息
    messages = [
        SystemMessage(content=prompt),
    ]

    if history_context:
        messages.append(HumanMessage(content=f"【对话历史】\n{history_context}\n\n【用户问题】\n{question}"))
    else:
        messages.append(HumanMessage(content=f"用户问题: {question}"))

    # 调用 LLM 生成 SQL
    logger.debug("调用 LLM 生成 SQL...")
    sql = llm.invoke(messages)
    sql = sql.strip() if sql else ""
    # 防御性剥除 LLM 可能返回的 markdown 代码块
    import re as _re
    sql = _re.sub(r'^```(?:sql)?\s*\n?', '', sql, flags=_re.IGNORECASE)
    sql = _re.sub(r'\n?```\s*$', '', sql).strip()
    logger.debug(f"生成的 SQL: {sql[:100]}...")

    # 处理无效 SQL
    if sql == "INVALID_SQL" or not sql:
        logger.warning("SQL 生成失败，返回 INVALID_SQL")
        return {
            "sql": {
                "generated_sql": None,
                "sql_error": "无法为该问题生成有效的 SQL",
            },
            "current_step": WorkflowStep.SQL_GENERATION,
        }

    logger.info(f"SQL 生成成功，长度: {len(sql)} 字符")
    return {
        "sql": {"generated_sql": sql},
        "current_step": WorkflowStep.SQL_GENERATION,
    }