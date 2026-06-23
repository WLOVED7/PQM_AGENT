"""
=============================================================================
数据库 Schema 定义 (db/schema.py)
=============================================================================

【用途】
定义 sip_records 单表结构，用于：
1. SQL 生成时的字段映射
2. 字段同义词匹配
3. 类型推断

【注意】
这是参考用的数据结构，不是 ORM 模型。
"""

# =============================================================================
# 表: sip_records (SIP 检验记录扁平表)
# 每行对应一个检验项目，包含完整的文档头信息
# =============================================================================
SIP_RECORDS_SCHEMA = {
    "table_name": "sip_records",
    "comment": "SIP 检验记录扁平表",
    "columns": {
        "id": {
            "type": "INT",
            "comment": "主键",
            "is_primary_key": True,
        },
        "project": {
            "type": "VARCHAR(100)",
            "comment": "项目号",
            "examples": ["SA2HG", "E2", "NP39"],
        },
        "customer": {
            "type": "VARCHAR(100)",
            "comment": "客户名称",
            "examples": ["比亚迪", "特斯拉", "蔚来"],
        },
        "document_id": {
            "type": "VARCHAR(100)",
            "comment": "文件号",
            "examples": ["VHST-SIP-SA2HG-008"],
        },
        "part_num": {
            "type": "VARCHAR(100)",
            "comment": "零件号",
            "examples": ["54246-5101311"],
        },
        "part_name": {
            "type": "VARCHAR(200)",
            "comment": "零件名称",
            "examples": ["前横梁", "后保险杠", "车门"],
        },
        "process": {
            "type": "VARCHAR(200)",
            "comment": "工序",
            "nullable": True,
            "examples": ["来料", "热压", "镭射", "落料"],
        },
        "mold_num": {
            "type": "VARCHAR(100)",
            "comment": "模具号",
            "nullable": True,
            "examples": ["HSTD200337"],
        },
        "inspection_item": {
            "type": "VARCHAR(500)",
            "comment": "检验项",
            "examples": ["外观检验", "材料厚度", "机械性能", "化学成分"],
        },
        "specification": {
            "type": "TEXT",
            "comment": "规范或描述（检验要求）",
            "nullable": True,
            "examples": ["表面无生锈、变形、划伤", "2±0.05mm", "抗拉强度≥515MPa"],
        },
        "inspection_method": {
            "type": "TEXT",
            "comment": "检验方法",
            "nullable": True,
            "examples": ["目视", "卡尺", "万能试验机", "直读光谱仪"],
        },
        "inspection_frequency": {
            "type": "VARCHAR(200)",
            "comment": "检查频次",
            "nullable": True,
            "examples": ["100%检验", "AQL 0.65/每批", "3PCS/每批"],
        },
        "version": {
            "type": "VARCHAR(20)",
            "comment": "版本号",
            "examples": ["A/3", "B/0", "A/6"],
        },
        "chunk_text": {
            "type": "TEXT",
            "comment": "RAG 检索文本块（自动生成）",
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
# 所有表 Schema 汇总
# =============================================================================
ALL_SCHEMAS = {
    "sip_records": SIP_RECORDS_SCHEMA,
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
    logger.debug(f"Schema: {get_table_schema('sip_records')}")
