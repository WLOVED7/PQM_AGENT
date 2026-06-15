"""
=============================================================================
RAG Retrieval Node (agents/rag/rag_retrieval_node.py)
=============================================================================

【核心功能】
从 RagFlow 知识库检索相关文档，并用 LLM 综合生成简洁答案。

【工作流程】
用户问题 → RagFlow 检索 chunks → LLM 综合 → rag_result
"""
from langchain_core.messages import HumanMessage, SystemMessage

from app.agents.base.llm import create_chat_llm
from app.state.state import AgentState, WorkflowStep
from app.tools.ragflow_client import get_ragflow_client
from app.utils.logger import get_logger

logger = get_logger(__name__)

RAG_SYNTHESIS_PROMPT = """你是质量检验知识库专家。根据检索文档回答用户问题。

【输出格式】
按 5M1E 维度组织，格式如下：

### 👤 人员
- 条目

---

### ⚙️ 设备
- 条目

---

（以此类推：📦 材料 / 📋 方法 / 📐 测量 / 🌡️ 环境）

【规则】
- 保留文档中所有条目，不得删减条数
- 每条只去掉多余的解释说明，保留核心结论和关键数值，控制在 30 字以内
- 若问题只问原因，只输出原因；只问对策，只输出对策；两者都问则在每个维度内先列"**原因：**"再列"**对策：**"
- 若某维度无相关内容则跳过

【检索文档】
{context}

【用户问题】
{question}"""


async def rag_retrieval_node(state: AgentState) -> AgentState:
    logger.info(f"RAG Retrieval 开始处理问题: {state['question'][:50]}...")

    question = state["question"]

    try:
        client = get_ragflow_client()
        raw = await client.retrieval(query=question, top_k=5)

        chunks = raw.get("chunks", [])
        answer = raw.get("answer", "")

        if not chunks and not answer:
            return {
                "rag": {"retrieved_docs": [], "answer": "未找到相关文档"},
                "current_step": WorkflowStep.RAG_RETRIEVAL,
            }

        # 拼接 chunks 作为上下文
        context = "\n\n".join(c.get("content", "") for c in chunks) if chunks else answer

        # LLM 综合生成简洁答案
        llm = create_chat_llm()
        prompt = RAG_SYNTHESIS_PROMPT.format(context=context, question=question)
        result = llm.invoke([
            SystemMessage(content="你是质量检验专家，擅长提炼知识库内容。"),
            HumanMessage(content=prompt),
        ])

        logger.info(f"RAG 综合完成，回答长度: {len(result)} 字符")

        return {
            "rag": {"retrieved_docs": [], "answer": result},
            "current_step": WorkflowStep.RAG_RETRIEVAL,
        }

    except Exception as e:
        logger.error(f"RAG 检索失败: {e}")
        return {
            "rag": {"retrieved_docs": [], "answer": f"RAG 检索失败: {str(e)}"},
            "current_step": WorkflowStep.RAG_RETRIEVAL,
        }
