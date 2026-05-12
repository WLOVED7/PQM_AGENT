-- =====================================================
-- PQM 质量检验知识库 - MySQL 建表 SQL
-- =====================================================

-- 创建数据库
CREATE DATABASE IF NOT EXISTS pqm_db
CHARACTER SET utf8mb4
COLLATE utf8mb4_unicode_ci;

USE pqm_db;

-- =====================================================
-- 1. documents 表 - 文档主表
-- =====================================================
CREATE TABLE IF NOT EXISTS documents (
    id INT AUTO_INCREMENT PRIMARY KEY COMMENT '主键',
    document_id VARCHAR(100) NOT NULL COMMENT '文档编号',
    customer VARCHAR(100) NOT NULL COMMENT '客户名称',
    project VARCHAR(100) NOT NULL COMMENT '项目名称',
    part_num VARCHAR(100) NOT NULL COMMENT '零件号',
    part_name VARCHAR(200) NOT NULL COMMENT '零件名称',
    document_type VARCHAR(50) NOT NULL COMMENT '文档类型',
    version VARCHAR(20) NOT NULL COMMENT '版本号',
    drawing_version VARCHAR(20) COMMENT '图纸版本',
    mold_num VARCHAR(100) COMMENT '模具编号',
    prepared_date DATE COMMENT '编制日期',
    status VARCHAR(20) NOT NULL DEFAULT 'active' COMMENT '状态',
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',

    UNIQUE KEY uk_document_id (document_id),
    INDEX idx_customer (customer),
    INDEX idx_project (project),
    INDEX idx_part_num (part_num),
    INDEX idx_document_type (document_type),
    INDEX idx_status (status),
    INDEX idx_customer_project (customer, project),
    INDEX idx_document_type_status (document_type, status),
    INDEX idx_part_num_version (part_num, version)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='文档主表';


-- =====================================================
-- 2. inspection_items 表 - 检验项目表
-- =====================================================
CREATE TABLE IF NOT EXISTS inspection_items (
    id INT AUTO_INCREMENT PRIMARY KEY COMMENT '主键',
    item_id VARCHAR(50) NOT NULL COMMENT '检验项目编号',
    document_id VARCHAR(100) NOT NULL COMMENT '文档编号',
    inspection_id INT NOT NULL COMMENT '检验顺序号',
    inspection_item VARCHAR(500) NOT NULL COMMENT '检验项目名称',
    special_characteristic VARCHAR(50) COMMENT '特殊特性',
    characteristic_level VARCHAR(10) COMMENT '特性等级: A, B, C',
    requirements JSON COMMENT '检验要求列表',
    inspection_method JSON COMMENT '检验方法列表',
    sampling_plan JSON COMMENT '抽样计划',
    source_page INT COMMENT '来源页码',
    chunk_text TEXT COMMENT '文本块 (用于RAG检索)',
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',

    UNIQUE KEY uk_item_id (item_id),
    INDEX idx_document_id (document_id),
    INDEX idx_inspection_id (inspection_id),
    INDEX idx_inspection_item (inspection_item),
    INDEX idx_characteristic_level (characteristic_level),
    INDEX idx_document_inspection (document_id, inspection_id),
    FULLTEXT INDEX idx_chunk_text_fulltext (chunk_text),

    CONSTRAINT fk_inspection_document
        FOREIGN KEY (document_id) REFERENCES documents(document_id)
        ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='检验项目表';


-- =====================================================
-- 3. document_changes 表 - 文档变更记录表
-- =====================================================
CREATE TABLE IF NOT EXISTS document_changes (
    id INT AUTO_INCREMENT PRIMARY KEY COMMENT '主键',
    change_id VARCHAR(50) NOT NULL COMMENT '变更编号',
    document_id VARCHAR(100) NOT NULL COMMENT '文档编号',
    version VARCHAR(20) NOT NULL COMMENT '版本号',
    change_date DATE NOT NULL COMMENT '变更日期',
    change_content VARCHAR(1000) NOT NULL COMMENT '变更内容',
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',

    UNIQUE KEY uk_change_id (change_id),
    INDEX idx_document_id (document_id),
    INDEX idx_version (version),
    INDEX idx_change_date (change_date),
    INDEX idx_document_version (document_id, version),

    CONSTRAINT fk_change_document
        FOREIGN KEY (document_id) REFERENCES documents(document_id)
        ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='文档变更记录表';


-- =====================================================
-- 视图: 文档完整信息视图 (含检验项目数量)
-- =====================================================
CREATE OR REPLACE VIEW v_document_complete AS
SELECT
    d.document_id,
    d.customer,
    d.project,
    d.part_num,
    d.part_name,
    d.document_type,
    d.version,
    d.drawing_version,
    d.mold_num,
    d.prepared_date,
    d.status,
    d.created_at,
    d.updated_at,
    COUNT(DISTINCT i.id) AS inspection_item_count,
    COUNT(DISTINCT c.id) AS change_count
FROM documents d
LEFT JOIN inspection_items i ON d.document_id = i.document_id
LEFT JOIN document_changes c ON d.document_id = c.document_id
GROUP BY d.document_id;


-- =====================================================
-- 视图: 检验项目完整信息视图
-- =====================================================
CREATE OR REPLACE VIEW v_inspection_item_complete AS
SELECT
    i.id,
    i.item_id,
    i.document_id,
    i.inspection_id,
    i.inspection_item,
    i.special_characteristic,
    i.characteristic_level,
    i.requirements,
    i.inspection_method,
    i.sampling_plan,
    i.source_page,
    i.chunk_text,
    i.created_at,
    i.updated_at,
    d.customer,
    d.project,
    d.part_num,
    d.part_name,
    d.document_type,
    d.version
FROM inspection_items i
JOIN documents d ON i.document_id = d.document_id;
