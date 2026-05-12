"""
=============================================================================
SQL 生成器 (tools/sql_generator.py)
=============================================================================

【核心功能】
将自然语言转换为 SQL 查询语句。

【工作流程】
1. 接收用户问题
2. 结合 Schema 上下文构造 Prompt
3. 调用 LLM 生成 SQL
4. 校验 SQL 安全性
5. 返回安全 SQL

【Prompt 设计要点】
- 只生成 SELECT 语句
- 严格遵循 Schema
- 使用正确的字段名和表名
"""

from typing import Optional, Tuple
from app.tools.schema_loader import schema_loader
from app.tools.sql_validator import sql_validator, SQLValidationError
from app.core.config import settings
from app.agents.base.llm import BaseLLM, get_llm


# =============================================================================
# SQL 生成 Prompt 模板
# =============================================================================
SQL_GENERATOR_PROMPT = """你是质量检验知识库的 SQL 生成专家。

【任务】
根据用户问题，生成准确的 SELECT 查询语句。

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

用户问题: 比亚迪项目有哪些SIP？
SQL:
SELECT document_id, part_name, version
FROM documents
WHERE customer = '比亚迪'
  AND document_type = 'SIP'
  AND status = 'active'
"""


class SQLGenerator:
    """SQL 生成器"""

    def __init__(self, llm_client: BaseLLM = None):
        """
        初始化 SQL 生成器

        Args:
            llm_client: LLM 客户端（如果不提供，使用默认客户端）
        """
        self.llm_client = llm_client or get_llm()
        self.validator = sql_validator

    def _build_context(self) -> Tuple[str, str]:
        """构建 Prompt 上下文"""
        schema_context = schema_loader.generate_schema_context()
        synonym_context = schema_loader.generate_synonym_context()
        return schema_context, synonym_context

    async def generate(self, user_question: str) -> str:
        """
        生成 SQL

        Args:
            user_question: 用户问题

        Returns:
            生成的 SQL 语句

        Raises:
            SQLValidationError: SQL 校验失败
        """
        schema_context, synonym_context = self._build_context()

        prompt = SQL_GENERATOR_PROMPT.format(
            schema_context=schema_context,
            synonym_context=synonym_context,
        )

        # 添加用户问题
        full_prompt = f"{prompt}\n\n【用户问题】\n{user_question}"

        # 调用 LLM（异步）
        sql = await self.llm_client.generate(
            system="你是一个SQL生成专家，只输出SQL语句。",
            user_message=full_prompt,
        )

        # 清理 SQL
        sql = sql.strip()

        # 校验 SQL
        if sql == "INVALID_SQL" or not sql:
            raise SQLValidationError("无法为该问题生成有效的 SQL")

        sql = self.validator.validate_and_sanitize(sql)

        return sql


class SQLGeneratorWithLLM(SQLGenerator):
    """使用真实 LLM 的 SQL 生成器"""

    def __init__(self, llm_client):
        super().__init__(llm_client=llm_client)


# 全局实例
sql_generator = SQLGenerator()
