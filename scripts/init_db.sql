-- =====================================================
-- PQM 质量检验知识库 - PostgreSQL 建表 SQL
-- =====================================================

-- =====================================================
-- 自动更新 updated_at 的触发器函数
-- =====================================================
CREATE OR REPLACE FUNCTION update_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;


-- =====================================================
-- 1. documents 表 - 文档主表
-- =====================================================
CREATE TABLE IF NOT EXISTS documents (
    id SERIAL PRIMARY KEY,
    document_id VARCHAR(100) NOT NULL,
    customer VARCHAR(100) NOT NULL,
    project VARCHAR(100) NOT NULL,
    part_num VARCHAR(100) NOT NULL,
    part_name VARCHAR(200) NOT NULL,
    document_type VARCHAR(50) NOT NULL,
    version VARCHAR(20) NOT NULL,
    drawing_version VARCHAR(20),
    mold_num VARCHAR(100),
    prepared_date DATE,
    status VARCHAR(20) NOT NULL DEFAULT 'active',
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,

    CONSTRAINT uk_document_id UNIQUE (document_id)
);

COMMENT ON TABLE documents IS '文档主表';
COMMENT ON COLUMN documents.document_id IS '文档编号';
COMMENT ON COLUMN documents.customer IS '客户名称';
COMMENT ON COLUMN documents.project IS '项目名称';
COMMENT ON COLUMN documents.part_num IS '零件号';
COMMENT ON COLUMN documents.part_name IS '零件名称';
COMMENT ON COLUMN documents.document_type IS '文档类型';
COMMENT ON COLUMN documents.version IS '版本号';
COMMENT ON COLUMN documents.status IS '状态';

CREATE INDEX IF NOT EXISTS idx_customer ON documents (customer);
CREATE INDEX IF NOT EXISTS idx_project ON documents (project);
CREATE INDEX IF NOT EXISTS idx_part_num ON documents (part_num);
CREATE INDEX IF NOT EXISTS idx_document_type ON documents (document_type);
CREATE INDEX IF NOT EXISTS idx_status ON documents (status);
CREATE INDEX IF NOT EXISTS idx_customer_project ON documents (customer, project);
CREATE INDEX IF NOT EXISTS idx_document_type_status ON documents (document_type, status);
CREATE INDEX IF NOT EXISTS idx_part_num_version ON documents (part_num, version);

DROP TRIGGER IF EXISTS trg_documents_updated_at ON documents;
CREATE TRIGGER trg_documents_updated_at
    BEFORE UPDATE ON documents
    FOR EACH ROW EXECUTE FUNCTION update_updated_at();


-- =====================================================
-- 2. inspection_items 表 - 检验项目表
-- =====================================================
CREATE TABLE IF NOT EXISTS inspection_items (
    id SERIAL PRIMARY KEY,
    item_id VARCHAR(50) NOT NULL,
    document_id VARCHAR(100) NOT NULL,
    inspection_id INT NOT NULL,
    inspection_item VARCHAR(500) NOT NULL,
    special_characteristic VARCHAR(50),
    characteristic_level VARCHAR(10),
    requirements JSONB,
    inspection_method JSONB,
    sampling_plan JSONB,
    source_page INT,
    chunk_text TEXT,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,

    CONSTRAINT uk_item_id UNIQUE (item_id),
    CONSTRAINT fk_inspection_document
        FOREIGN KEY (document_id) REFERENCES documents(document_id)
        ON DELETE CASCADE
);

COMMENT ON TABLE inspection_items IS '检验项目表';
COMMENT ON COLUMN inspection_items.inspection_item IS '检验项目名称';
COMMENT ON COLUMN inspection_items.characteristic_level IS '特性等级: A, B, C';
COMMENT ON COLUMN inspection_items.chunk_text IS '文本块 (用于RAG检索)';

CREATE INDEX IF NOT EXISTS idx_ii_document_id ON inspection_items (document_id);
CREATE INDEX IF NOT EXISTS idx_ii_inspection_id ON inspection_items (inspection_id);
CREATE INDEX IF NOT EXISTS idx_ii_inspection_item ON inspection_items (inspection_item);
CREATE INDEX IF NOT EXISTS idx_ii_characteristic_level ON inspection_items (characteristic_level);
CREATE INDEX IF NOT EXISTS idx_ii_document_inspection ON inspection_items (document_id, inspection_id);
CREATE INDEX IF NOT EXISTS idx_chunk_text_fulltext ON inspection_items
    USING gin(to_tsvector('simple', COALESCE(chunk_text, '')));

DROP TRIGGER IF EXISTS trg_inspection_items_updated_at ON inspection_items;
CREATE TRIGGER trg_inspection_items_updated_at
    BEFORE UPDATE ON inspection_items
    FOR EACH ROW EXECUTE FUNCTION update_updated_at();


-- =====================================================
-- 3. document_changes 表 - 文档变更记录表
-- =====================================================
CREATE TABLE IF NOT EXISTS document_changes (
    id SERIAL PRIMARY KEY,
    change_id VARCHAR(50) NOT NULL,
    document_id VARCHAR(100) NOT NULL,
    version VARCHAR(20) NOT NULL,
    change_date DATE NOT NULL,
    change_content VARCHAR(1000) NOT NULL,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,

    CONSTRAINT uk_change_id UNIQUE (change_id),
    CONSTRAINT fk_change_document
        FOREIGN KEY (document_id) REFERENCES documents(document_id)
        ON DELETE CASCADE
);

COMMENT ON TABLE document_changes IS '文档变更记录表';

CREATE INDEX IF NOT EXISTS idx_dc_document_id ON document_changes (document_id);
CREATE INDEX IF NOT EXISTS idx_dc_version ON document_changes (version);
CREATE INDEX IF NOT EXISTS idx_dc_change_date ON document_changes (change_date);
CREATE INDEX IF NOT EXISTS idx_dc_document_version ON document_changes (document_id, version);

DROP TRIGGER IF EXISTS trg_document_changes_updated_at ON document_changes;
CREATE TRIGGER trg_document_changes_updated_at
    BEFORE UPDATE ON document_changes
    FOR EACH ROW EXECUTE FUNCTION update_updated_at();


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
GROUP BY
    d.document_id, d.customer, d.project, d.part_num, d.part_name,
    d.document_type, d.version, d.drawing_version, d.mold_num,
    d.prepared_date, d.status, d.created_at, d.updated_at;


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
