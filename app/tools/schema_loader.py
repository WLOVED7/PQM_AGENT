"""
=============================================================================
Schema 加载器 + 字段同义词映射 (tools/schema_loader.py)
=============================================================================

【核心功能】
1. 字段同义词映射（工业场景核心）
2. 生成 SQL 所需的上下文

【为什么需要同义词映射？】
用户说："前横梁的厚度要求是多少？"
数据库字段是：inspection_item, specification

需要映射：
  "厚度" → "inspection_item"
  "要求" → "specification"

这是工业 Agent 的核心，不是让 LLM 自由发挥。
"""

from typing import Dict, List, Optional, Any
from app.db.schema import ALL_SCHEMAS


# =============================================================================
# 字段同义词映射（工业场景专用）
# =============================================================================
# key: 用户可能说的词 -> value: 数据库实际字段名

FIELD_SYNONYMS: Dict[str, str] = {
    # -------- 文档头字段 --------

    # 项目相关
    "项目": "project",
    "项目名称": "project",
    "项目号": "project",

    # 客户相关
    "客户": "customer",
    "甲方": "customer",
    "客户名称": "customer",
    "顾客": "customer",

    # 文件/文档相关
    "文档": "document_id",
    "文档编号": "document_id",
    "文件号": "document_id",
    "文件编号": "document_id",
    "SIP编号": "document_id",

    # 零件相关
    "零件": "part_name",
    "零件名称": "part_name",
    "零件号": "part_num",
    "件号": "part_num",
    "件名": "part_name",

    # 模具相关
    "模具": "mold_num",
    "模具号": "mold_num",
    "模具编号": "mold_num",

    # 工序相关
    "工序": "process",
    "制程": "process",
    "工艺": "process",
    "加工工序": "process",
    "工艺工序": "process",
    # 常见工序名称（告知 LLM 这些词是 process 字段的值）
    "来料": "process",
    "来料检验": "process",
    "热压": "process",
    "热压工序": "process",
    "镭射": "process",
    "落料": "process",

    # 版本相关
    "版本": "version",
    "版本号": "version",

    # -------- 检验项目字段 --------

    # 检验项相关
    "检验项目": "inspection_item",
    "检验项": "inspection_item",
    "检验名称": "inspection_item",
    "检验类型": "inspection_item",
    "检查项目": "inspection_item",
    "检查名称": "inspection_item",

    # 规范/描述相关
    "要求": "specification",
    "检验要求": "specification",
    "标准": "specification",
    "标准要求": "specification",
    "规格": "specification",
    "规范": "specification",
    "描述": "specification",
    "硬度标准": "specification",
    "尺寸标准": "specification",
    "外观标准": "specification",

    # 检验方法相关
    "方法": "inspection_method",
    "检验方法": "inspection_method",
    "检测方法": "inspection_method",
    "测量方法": "inspection_method",
    "用什么检查": "inspection_method",
    "怎么检查": "inspection_method",

    # 检查频次相关
    "AQL": "inspection_frequency",
    "抽样": "inspection_frequency",
    "抽样计划": "inspection_frequency",
    "检验水平": "inspection_frequency",
    "检查频次": "inspection_frequency",
    "频次": "inspection_frequency",
    "检验频率": "inspection_frequency",
}


# =============================================================================
# 数值条件词映射
# =============================================================================
OPERATOR_SYNONYMS: Dict[str, str] = {
    # 比较运算符
    "大于": ">",
    "小于": "<",
    "大于等于": ">=",
    "小于等于": "<=",
    "等于": "=",
    "不等于": "!=",
    "不是": "!=",
    "是": "=",
    "在": "IN",
    "不在": "NOT IN",
    "之间": "BETWEEN",

    # 模糊匹配
    "包含": "LIKE",
    "含有": "LIKE",
    "有": "LIKE",
    "没有": "NOT LIKE",
    "不含": "NOT LIKE",
}


# =============================================================================
# 业务实体名称映射（表名）
# =============================================================================
TABLE_SYNONYMS: Dict[str, str] = {
    "SIP": "sip_records",
    "SIP记录": "sip_records",
    "SIP文档": "sip_records",
    "检验记录": "sip_records",
    "检验项目": "sip_records",
    "检验标准": "sip_records",
    "检验规程": "sip_records",
    "文档": "sip_records",
    "记录": "sip_records",
}


# =============================================================================
# Schema 加载器类
# =============================================================================
class SchemaLoader:
    """Schema 加载器"""

    def __init__(self):
        self.schemas = ALL_SCHEMAS
        self.field_synonyms = FIELD_SYNONYMS
        self.operator_synonyms = OPERATOR_SYNONYMS
        self.table_synonyms = TABLE_SYNONYMS

    def get_table_columns(self, table_name: str) -> List[str]:
        """获取表的所有列名"""
        schema = self.schemas.get(table_name)
        if not schema:
            return []
        return list(schema["columns"].keys())

    def get_table_comment(self, table_name: str) -> str:
        """获取表注释"""
        schema = self.schemas.get(table_name)
        return schema.get("comment", "") if schema else ""

    def get_column_info(self, table_name: str, column_name: str) -> Optional[Dict]:
        """获取列的详细信息"""
        schema = self.schemas.get(table_name)
        if not schema:
            return None
        return schema["columns"].get(column_name)

    def resolve_field(self, user_word: str) -> Optional[str]:
        """将用户说的词解析为数据库字段名"""
        return self.field_synonyms.get(user_word)

    def resolve_table(self, user_word: str) -> Optional[str]:
        """将用户说的词解析为表名"""
        return self.table_synonyms.get(user_word)

    def resolve_operator(self, user_word: str) -> Optional[str]:
        """将用户说的词解析为运算符"""
        return self.operator_synonyms.get(user_word)

    def generate_schema_context(self) -> str:
        """生成用于 LLM 的 schema 上下文"""
        lines = []
        lines.append("=" * 60)
        lines.append("数据库 Schema 上下文")
        lines.append("=" * 60)

        for table_name, schema in self.schemas.items():
            lines.append(f"\n【{table_name}】 - {schema['comment']}")
            lines.append("-" * 40)

            for col_name, col_info in schema["columns"].items():
                comment = col_info.get("comment", "")
                col_type = col_info.get("type", "")
                examples = col_info.get("examples", [])

                line = f"  {col_name} ({col_type})"
                if comment:
                    line += f" - {comment}"
                lines.append(line)

                if examples:
                    lines.append(f"    示例: {examples[:3]}")

        lines.append("=" * 60)

        return "\n".join(lines)

    def generate_synonym_context(self) -> str:
        """生成字段同义词上下文（帮助 LLM 理解用户意图）"""
        lines = []
        lines.append("=" * 60)
        lines.append("字段同义词映射（用户说 → 数据库字段）")
        lines.append("=" * 60)

        tables = {}
        for user_word, db_field in self.field_synonyms.items():
            for table_name, schema in self.schemas.items():
                if db_field in schema["columns"]:
                    if table_name not in tables:
                        tables[table_name] = []
                    tables[table_name].append(f"  「{user_word}」 → {db_field}")
                    break

        for table_name, mappings in tables.items():
            lines.append(f"\n【{table_name}】")
            for m in mappings:
                lines.append(m)

        lines.append("=" * 60)
        return "\n".join(lines)


# 全局实例
schema_loader = SchemaLoader()
