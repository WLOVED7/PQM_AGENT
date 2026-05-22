"""
=============================================================================
数据库 Schema 定义 (db/schema.py)
=============================================================================

【用途】
定义三张业务表的结构，用于：
1. SQL 生成时的字段映射
2. 字段同义词匹配
3. 类型推断

【注意】
这是参考用的数据结构，不是 ORM 模型。
"""

# =============================================================================
# 表1: documents (SIP 主表)
# =============================================================================
DOCUMENTS_SCHEMA = {
    "table_name": "documents",
    "comment": "SIP 主表",
    "columns": {
        "id": {
            "type": "INT",
            "comment": "主键",
            "is_primary_key": True,
        },
        "document_id": {
            "type": "VARCHAR(100)",
            "comment": "文档编号【唯一】",
            "is_unique": True,
        },
        "customer": {
            "type": "VARCHAR(100)",
            "comment": "客户名称",
            "examples": ["比亚迪", "特斯拉", "蔚来"],
        },
        "project": {
            "type": "VARCHAR(100)",
            "comment": "项目名称",
            "examples": ["SA2HG", "E2", "NP39"],
        },
        "part_num": {
            "type": "VARCHAR(100)",
            "comment": "零件号",
            "examples": ["SA2HG-5101311"],
        },
        "part_name": {
            "type": "VARCHAR(200)",
            "comment": "零件名称",
            "examples": ["前横梁", "后保险杠", "车门"],
        },
        "document_type": {
            "type": "VARCHAR(50)",
            "comment": "文档类型 (SIP/SOP)",
            "examples": ["SIP", "SOP"],
        },
        "version": {
            "type": "VARCHAR(20)",
            "comment": "版本号",
            "examples": ["A/6", "B/0"],
        },
        "drawing_version": {
            "type": "VARCHAR(20)",
            "comment": "图纸版本",
            "nullable": True,
        },
        "mold_num": {
            "type": "VARCHAR(100)",
            "comment": "模具编号",
            "nullable": True,
        },
        "prepared_date": {
            "type": "DATE",
            "comment": "编制日期",
            "nullable": True,
        },
        "status": {
            "type": "VARCHAR(20)",
            "comment": "状态 (active/inactive)",
            "examples": ["active", "inactive", "archived"],
        },
        "created_at": {
            "type": "DATETIME",
            "comment": "创建时间",
        },
        "updated_at": {
            "type": "DATETIME",
            "comment": "更新时间",
        },
    }
}


# =============================================================================
# 表2: inspection_items (检验项目表)
# =============================================================================
INSPECTION_ITEMS_SCHEMA = {
    "table_name": "inspection_items",
    "comment": "检验项目表",
    "columns": {
        "id": {
            "type": "INT",
            "comment": "主键",
            "is_primary_key": True,
        },
        "item_id": {
            "type": "VARCHAR(50)",
            "comment": "检验项目编号【唯一】",
            "is_unique": True,
        },
        "document_id": {
            "type": "VARCHAR(100)",
            "comment": "外键 → documents.document_id",
            "is_foreign_key": True,
            "references": "documents.document_id",
        },
        "inspection_id": {
            "type": "INT",
            "comment": "检验顺序号",
        },
        "inspection_item": {
            "type": "VARCHAR(500)",
            "comment": "检验项目名称",
            "examples": ["外观检验", "尺寸检验", "硬度检验", "材料成分检验"],
        },
        "special_characteristic": {
            "type": "VARCHAR(50)",
            "comment": "特殊特性 (SF)",
            "nullable": True,
        },
        "characteristic_level": {
            "type": "VARCHAR(10)",
            "comment": "特性等级 (A/B/C)",
            "examples": ["A", "B", "C"],
        },
        "requirements": {
            "type": "JSON",
            "comment": "检验要求列表",
            "examples": [["不允许有生锈", "长度500±0.5mm"], ["HRC 45-55"]],
        },
        "inspection_method": {
            "type": "JSON",
            "comment": "检验方法列表",
            "examples": [["目视", "卡尺"], ["三坐标测量机"]],
        },
        "sampling_plan": {
            "type": "JSON",
            "comment": "抽样计划",
            "examples": [{"type": "OQC", "aql": "0.65", "inspection_level": "II"}],
        },
        "source_page": {
            "type": "INT",
            "comment": "来源页码",
            "nullable": True,
        },
        "chunk_text": {
            "type": "TEXT",
            "comment": "文本块 (用于RAG)",
            "nullable": True,
        },
        "created_at": {
            "type": "DATETIME",
            "comment": "创建时间",
        },
        "updated_at": {
            "type": "DATETIME",
            "comment": "更新时间",
        },
    }
}


# =============================================================================
# 表3: document_changes (变更记录表)
# =============================================================================
DOCUMENT_CHANGES_SCHEMA = {
    "table_name": "document_changes",
    "comment": "版本变更记录表",
    "columns": {
        "id": {
            "type": "INT",
            "comment": "主键",
            "is_primary_key": True,
        },
        "change_id": {
            "type": "VARCHAR(50)",
            "comment": "变更编号【唯一】",
            "is_unique": True,
        },
        "document_id": {
            "type": "VARCHAR(100)",
            "comment": "外键 → documents.document_id",
            "is_foreign_key": True,
            "references": "documents.document_id",
        },
        "version": {
            "type": "VARCHAR(20)",
            "comment": "版本号",
        },
        "change_date": {
            "type": "DATE",
            "comment": "变更日期",
        },
        "change_content": {
            "type": "VARCHAR(1000)",
            "comment": "变更内容",
        },
        "created_at": {
            "type": "DATETIME",
            "comment": "创建时间",
        },
    }
}


# =============================================================================
# 表关系
# =============================================================================
TABLE_RELATIONSHIPS = [
    {
        "from_table": "inspection_items",
        "from_column": "document_id",
        "to_table": "documents",
        "to_column": "document_id",
        "relationship": "N:1",  # N个检验项目属于1个文档
    },
    {
        "from_table": "document_changes",
        "from_column": "document_id",
        "to_table": "documents",
        "to_column": "document_id",
        "relationship": "N:1",  # N个变更记录属于1个文档
    },
]


# =============================================================================
# 所有表 Schema 汇总
# =============================================================================
ALL_SCHEMAS = {
    "documents": DOCUMENTS_SCHEMA,
    "inspection_items": INSPECTION_ITEMS_SCHEMA,
    "document_changes": DOCUMENT_CHANGES_SCHEMA,
}


def get_table_schema(table_name: str) -> dict:
    """获取指定表的 Schema"""
    return ALL_SCHEMAS.get(table_name)


def get_all_tables() -> list:
    """获取所有表名"""
    return list(ALL_SCHEMAS.keys())

if __name__ == "__main__":
    from app.utils.logger import get_logger
    logger = get_logger(__name__)
    logger.debug(f"Schema: {get_table_schema('documents')}")
    