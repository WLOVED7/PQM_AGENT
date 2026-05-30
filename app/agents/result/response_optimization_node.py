"""
=============================================================================
Response Optimization Node (agents/result/response_optimization_node.py)
=============================================================================

【核心功能】
对 result_aggregation 生成的原始结果进行自然语言润色，生成更友好的最终回复。

【工作流程】
result_aggregation (原始数据) → LLM 润色 → 最终回复

【优化内容】
1. JSON 数组格式化为列表显示
2. 数字/单位格式化
3. 结构化展示表格化结果
4. 自然语言总结
"""
from typing import Optional

from langchain_core.messages import HumanMessage, SystemMessage

from app.agents.base.llm import create_chat_llm
from app.state.state import AgentState, WorkflowStep
from app.utils.logger import get_logger

logger = get_logger(__name__)


OPTIMIZATION_PROMPT = """你是质量检验知识库的回复优化专家。

【原始问题】
{question}

【SQL 查询结果】
{raw_result}

【你的任务】
1. 将原始数据格式化为友好可读的回复
2. JSON 数组格式化为列表展示
3. 保持信息准确，简明扼要
4. 如有多条结果，使用编号列表

【示例】
原始: {"inspection_item": "外观检验", "requirements": "[\"不允许有生锈\", \"不允许有开裂\"]"}
优化: **外观检验**：
- 不允许有生锈
- 不允许有开裂

【输出格式】
直接输出优化后的回复，不要其他内容。"""


async def response_optimization_node(state: AgentState) -> AgentState:
    """
    Response Optimization Node

    【感知】接收 question 和原始结果
    【理解】理解数据结构
    【执行】生成格式化友好的最终回复

    Args:
        state: AgentState

    Returns:
        更新后的 state，包含 final_response
    """
    logger.info("Response Optimization 开始优化回复")

    question = state["question"]
    sql_domain = state.get("sql", {})
    rag_domain = state.get("rag", {})
    sql_result = sql_domain.get("sql_result")
    rag_result = rag_domain.get("answer")
    sql_error = sql_domain.get("sql_error")
    retry_exhausted = state.get("retry_exhausted", False)

    # 构建原始结果描述
    logger.debug("构建原始结果描述...")
    raw_result = _build_raw_result_description(
        sql_result=sql_result,
        rag_result=rag_result,
        sql_error=sql_error,
        retry_exhausted=retry_exhausted,
    )

    # 如果原始结果已经是简洁的友好格式（无SQL数据，只有RAG或错误），直接返回
    if not sql_result or not sql_result.get("success"):
        logger.info("跳过 LLM 优化，使用原始回复")
        logger.debug(f"原始回复: {raw_result[:100]}...")
        return {
            **state,
            "result": {
                **state.get("result", {}),
                "final_response": raw_result,
            },
            "current_step": WorkflowStep.RESPONSE_OPTIMIZATION,
        }

    # 调用 LLM 优化（需转义 raw_result 中的花括号，防止 str.format() 误解析）
    logger.debug("调用 LLM 优化回复...")
    try:
        llm = create_chat_llm()
        escaped_raw_result = raw_result.replace("{", "{{").replace("}", "}}")
        prompt = OPTIMIZATION_PROMPT.format(
            question=question,
            raw_result=escaped_raw_result,
        )

        messages = [
            SystemMessage(content="你是一个专业的质量检验知识库助手，擅长将原始数据格式化为友好的回复。"),
            HumanMessage(content=prompt),
        ]

        optimized_response = llm.invoke(messages)
        optimized_response = optimized_response.strip() if optimized_response else raw_result
    except Exception as e:
        logger.warning(f"LLM 优化失败，使用原始回复: {e}")
        optimized_response = raw_result

    logger.info(f"Response Optimization 完成，优化后回复长度: {len(optimized_response)} 字符")
    logger.debug(f"最终回复: {optimized_response[:100]}...")

    return {
        **state,
        "result": {
            **state.get("result", {}),
            "final_response": optimized_response,
        },
        "current_step": WorkflowStep.RESPONSE_OPTIMIZATION,
    }


def _format_row_for_display(row: dict) -> str:
    """格式化行数据为易读字符串"""
    parts = []
    for key, value in row.items():
        if value is None:
            continue
        # JSON 字符串解析
        if isinstance(value, str) and value.startswith('['):
            try:
                import json
                value = json.loads(value)
            except:
                pass
        # 格式化
        if isinstance(value, list):
            value = ' | '.join(str(v) for v in value)
        parts.append(f"{key}: {value}")
    return ", ".join(parts)


def _build_raw_result_description(
    sql_result: Optional[dict],
    rag_result: Optional[str],
    sql_error: Optional[str],
    retry_exhausted: bool,
) -> str:
    """构建原始结果的描述文本"""
    # SQL 执行成功
    if sql_result and sql_result.get("success"):
        data = sql_result.get("data", [])
        count = sql_result.get("count", 0)

        if count == 0:
            return "没有找到符合条件的数据。"

        # 构建原始数据描述
        lines = [f"找到 {count} 条结果：\n"]
        for i, row in enumerate(data, 1):
            row_str = _format_row_for_display(row)
            lines.append(f"{i}. {row_str}")

        if count > 10:
            lines.append(f"\n... 还有 {count - 10} 条结果未显示")

        return "\n".join(lines)

    # SQL 执行失败
    if sql_error:
        if rag_result and rag_result != "RAG 功能待完善":
            return f"数据库查询失败：{sql_error}\n\n另外，关于您的问题：\n{rag_result}"
        return f"抱歉，无法回答您的问题。数据库查询失败：{sql_error}"

    # RAG 结果
    if rag_result and rag_result != "RAG 功能待完善":
        return rag_result

    # 重试耗尽
    if retry_exhausted:
        return "抱歉，经过多次尝试后仍无法生成有效的 SQL 来回答您的问题。"

    return "抱歉，无法回答您的问题。"