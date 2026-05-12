"""
=============================================================================
Schema 加载器 + 字段同义词映射 (tools/schema_loader.py)
=============================================================================

【核心功能】
1. 从数据库动态加载表结构
2. 字段同义词映射（工业场景核心）
3. 生成 SQL 所需的上下文

【为什么需要同义词映射？】
用户说："前横梁硬度标准是多少？"
数据库字段是：inspection_item, requirements

需要映射：
  "硬度" → "inspection_item"
  "标准" → "requirements"

这是工业 Agent 的核心，不是让 LLM 自由发挥。
"""

from typing import Dict, List, Optional, Any
from app.db.schema import ALL_SCHEMAS, TABLE_RELATIONSHIPS


# =============================================================================
# 字段同义词映射（工业场景专用）
# =============================================================================
# key: 用户可能说的词 -> value: 数据库实际字段名

FIELD_SYNONYMS: Dict[str, str] = {
    # -------- documents 表 --------

    # 客户相关
    "客户": "customer",
    "甲方": "customer",
    "客户名称": "customer",
    "顾客": "customer",

    # 项目相关
    "项目": "project",
    "项目名称": "project",
    "项目号": "project",

    # 零件相关
    "零件": "part_name",
    "零件名称": "part_name",
    "零件号": "part_num",
    "件号": "part_num",
    "件名": "part_name",

    # 文档相关
    "文档": "document_id",
    "文档编号": "document_id",
    "SIP": "document_type",
    "SOP": "document_type",
    "文档类型": "document_type",

    # 版本相关
    "版本": "version",
    "版本号": "version",
    "图纸版本": "drawing_version",

    # 状态相关
    "状态": "status",
    "是否有效": "status",
    "有效": "status",

    # -------- inspection_items 表 --------

    # 检验项目相关
    "检验项目": "inspection_item",
    "检验名称": "inspection_item",
    "检验类型": "inspection_item",
    "检查项目": "inspection_item",
    "检查名称": "inspection_item",

    # 检验要求相关
    "要求": "requirements",
    "检验要求": "requirements",
    "标准": "requirements",
    "标准要求": "requirements",
    "规格": "requirements",
    "硬度标准": "requirements",
    "尺寸标准": "requirements",
    "外观标准": "requirements",

    # 检验方法相关
    "方法": "inspection_method",
    "检验方法": "inspection_method",
    "检测方法": "inspection_method",
    "测量方法": "inspection_method",
    "用什么检查": "inspection_method",
    "怎么检查": "inspection_method",

    # 抽样计划相关
    "AQL": "sampling_plan",
    "抽样": "sampling_plan",
    "抽样计划": "sampling_plan",
    "检验水平": "sampling_plan",
    "抽样标准": "sampling_plan",

    # 特性等级相关
    "特性等级": "characteristic_level",
    "等级": "characteristic_level",
    "级别": "characteristic_level",
    "A类": "characteristic_level",
    "B类": "characteristic_level",
    "C类": "characteristic_level",
    "A级": "characteristic_level",
    "B级": "characteristic_level",
    "C级": "characteristic_level",
    "关键特性": "characteristic_level",
    "重要特性": "characteristic_level",

    # 特殊特性
    "特殊特性": "special_characteristic",
    "SF": "special_characteristic",

    # -------- document_changes 表 --------

    # 变更相关
    "变更": "change_content",
    "变更内容": "change_content",
    "变更记录": "change_content",
    "变更日期": "change_date",
    "版本变更": "version",
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
    "不是": "!=",
    "在": "IN",
    "不在": "NOT IN",
    "之间": "BETWEEN",

    # 模糊匹配
    "包含": "LIKE",
    "含有": "LIKE",
    "有": "LIKE",
    "没有": "NOT LIKE",
    "不含": "NOT LIKE",

    # JSON 字段
    "AQL是": "JSON_EXTRACT",
    "AQL为": "JSON_EXTRACT",
}


# =============================================================================
# 业务实体名称映射（表名）
# =============================================================================
TABLE_SYNONYMS: Dict[str, str] = {
    # 文档表
    "文档": "documents",
    "SIP": "documents",
    "SIP文档": "documents",
    "检验标准": "documents",
    "检验规程": "documents",

    # 检验项目表
    "检验项目": "inspection_items",
    "检验项目表": "inspection_items",
    "检验明细": "inspection_items",
    "检查项目": "inspection_items",

    # 变更记录表
    "变更": "document_changes",
    "变更记录": "document_changes",
    "版本变更": "document_changes",
    "历史": "document_changes",
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
        self.relationships = TABLE_RELATIONSHIPS

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
                    lines.append(f"    示例: {examples[:3]}")  # 最多显示3个

        lines.append("\n" + "=" * 60)
        lines.append("表关系:")
        lines.append("-" * 40)
        for rel in self.relationships:
            lines.append(
                f"  {rel['from_table']}.{rel['from_column']} "
                f"→ {rel['to_table']}.{rel['to_column']} ({rel['relationship']})"
            )

        lines.append("=" * 60)

        return "\n".join(lines)

    def generate_synonym_context(self) -> str:
        """生成字段同义词上下文（帮助 LLM 理解用户意图）"""
        lines = []
        lines.append("=" * 60)
        lines.append("字段同义词映射（用户说 → 数据库字段）")
        lines.append("=" * 60)

        # 按表分组
        tables = {}
        for user_word, db_field in self.field_synonyms.items():
            # 找到字段属于哪个表
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
