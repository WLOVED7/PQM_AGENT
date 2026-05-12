"""
=============================================================================
SQL Agent Node (agents/sql/sql_agent_node.py)
=============================================================================

【核心功能】
将自然语言问题转换为 SQL 并执行。

【工作流程】
question → LLM 生成 SQL → 校验 → 执行 → 返回结果

【感知/理解/执行】
- 感知: 接收 question, session_history
- 理解: 结合 Schema 上下文理解查询需求
- 执行: 生成 SQL + 执行 + 返回结果
"""
from langchain_core.messages import HumanMessage, SystemMessage

from app.agents.base.llm import create_chat_llm
from app.graph.state import AgentState, WorkflowStep
from app.tools.schema_loader import schema_loader
from app.tools.sql_validator import SQLValidator, SQLValidationError
from app.db.connection import fetch_all


# =============================================================================
# SQL 生成 Prompt
# =============================================================================
SQL_GENERATION_PROMPT = """你是质量检验知识库的 SQL 生成专家。

【数据库 Schema】
{schema_context}

【字段同义词映射】
{synonym_context}

【重要规则】
1. 只生成 SELECT 语句，禁止生成 INSERT/UPDATE/DELETE/DROP
2. 表名必须使用: documents, inspection_items, document_changes
3. 字段名必须与 Schema 中完全一致
4. 字符串值用单引号包裹，如: customer = '比亚迪'
5. JSON 字段查询示例:
   - AQL=0.65: JSON_EXTRACT(sampling_plan, '$.aql') = '0.65'
   - requirements 包含'生锈': JSON_EXTRACT(requirements, '$[0]) LIKE '%生锈%'
6. 多表查询需要 JOIN:
   - inspection_items 和 documents 通过 document_id 关联
   - document_changes 和 documents 通过 document_id 关联
7. LIMIT 默认 100，最大不超过 100

【输出格式】
只输出 SQL 语句，不要其他内容。
如果无法生成 SQL，输出: INVALID_SQL

【示例】
用户问题: 前横梁的硬度标准是什么？
SQL:
SELECT i.inspection_item, i.requirements
FROM inspection_items i
JOIN documents d ON i.document_id = d.document_id
WHERE d.part_name = '前横梁'
  AND i.inspection_item LIKE '%硬度%'

用户问题: 哪些项目的AQL是0.65？
SQL:
SELECT DISTINCT d.project, d.part_name
FROM inspection_items i
JOIN documents d ON i.document_id = d.document_id
WHERE JSON_EXTRACT(i.sampling_plan, '$.aql') = '0.65'
"""


async def sql_agent_node(state: AgentState) -> AgentState:
    """
    SQL Agent Node - 生成并执行 SQL

    【感知】接收 question, session_history
    【理解】结合 Schema 上下文理解查询需求
    【执行】调用 LLM 生成 SQL，校验后执行

    Args:
        state: AgentState

    Returns:
        更新后的 state，包含 generated_sql, sql_result, sql_error
    """
    llm = create_chat_llm()
    question = state["question"]
    session_id = state["session_id"]

    # 获取对话历史上下文
    from app.agents.memory.session_memory import session_memory
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
    sql = llm.invoke(messages)
    sql = sql.strip() if sql else ""

    # 处理无效 SQL
    if sql == "INVALID_SQL" or not sql:
        return {
            **state,
            "generated_sql": None,
            "sql_result": None,
            "sql_error": "无法为该问题生成有效的 SQL",
            "current_step": WorkflowStep.SQL_AGENT,
        }

    # 校验 SQL
    validator = SQLValidator()
    try:
        sql = validator.validate_and_sanitize(sql)
    except SQLValidationError as e:
        return {
            **state,
            "generated_sql": sql,
            "sql_result": None,
            "sql_error": f"SQL 校验失败: {str(e)}",
            "current_step": WorkflowStep.SQL_AGENT,
        }

    # 执行 SQL
    result = {
        "success": False,
        "sql": sql,
        "data": None,
        "count": 0,
        "error": None,
    }

    try:
        data = await fetch_all(sql)
        # 限制返回行数
        if len(data) > 100:
            data = data[:100]
        result["success"] = True
        result["data"] = data
        result["count"] = len(data)
    except Exception as e:
        result["error"] = f"SQL 执行失败: {str(e)}"

    return {
        **state,
        "generated_sql": sql,
        "sql_result": result if result["success"] else None,
        "sql_error": result.get("error"),
        "current_step": WorkflowStep.SQL_AGENT,
    }