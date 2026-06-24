-- =====================================================
-- 热压品质异常预测系统 - PostgreSQL 建表 SQL
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
-- sip_records 表 - SIP 检验记录（扁平单表）
-- 每行对应一个检验项目，包含完整的文档头信息
-- =====================================================
CREATE TABLE IF NOT EXISTS sip_records (
    id                   SERIAL PRIMARY KEY,
    project              VARCHAR(100) NOT NULL,   -- 项目号
    customer             VARCHAR(100) NOT NULL,   -- 客户
    document_id          VARCHAR(100) NOT NULL,   -- 文件号
    part_num             VARCHAR(100) NOT NULL,   -- 零件号
    part_name            VARCHAR(200) NOT NULL,   -- 零件名称
    process              VARCHAR(200),            -- 工序
    mold_num             VARCHAR(100),            -- 模具号
    inspection_item      VARCHAR(500) NOT NULL,   -- 检验项
    specification        TEXT,                    -- 规范或描述
    inspection_method    TEXT,                    -- 检验方法
    inspection_frequency VARCHAR(200),            -- 检查频次
    version              VARCHAR(20)  NOT NULL,   -- 版本号
    chunk_text           TEXT,                    -- RAG 文本块
    created_at           TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at           TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT uq_sip_document_item UNIQUE (document_id, inspection_item)
);

COMMENT ON TABLE sip_records IS 'SIP 检验记录扁平表';
COMMENT ON COLUMN sip_records.project IS '项目号';
COMMENT ON COLUMN sip_records.customer IS '客户名称';
COMMENT ON COLUMN sip_records.document_id IS '文件号';
COMMENT ON COLUMN sip_records.part_num IS '零件号';
COMMENT ON COLUMN sip_records.part_name IS '零件名称';
COMMENT ON COLUMN sip_records.process IS '工序';
COMMENT ON COLUMN sip_records.mold_num IS '模具号';
COMMENT ON COLUMN sip_records.inspection_item IS '检验项';
COMMENT ON COLUMN sip_records.specification IS '规范或描述';
COMMENT ON COLUMN sip_records.inspection_method IS '检验方法';
COMMENT ON COLUMN sip_records.inspection_frequency IS '检查频次';
COMMENT ON COLUMN sip_records.version IS '版本号';
COMMENT ON COLUMN sip_records.chunk_text IS 'RAG 检索文本块';

CREATE INDEX IF NOT EXISTS idx_sr_customer ON sip_records (customer);
CREATE INDEX IF NOT EXISTS idx_sr_project ON sip_records (project);
CREATE INDEX IF NOT EXISTS idx_sr_document_id ON sip_records (document_id);
CREATE INDEX IF NOT EXISTS idx_sr_part_num ON sip_records (part_num);
CREATE INDEX IF NOT EXISTS idx_sr_inspection_item ON sip_records (inspection_item);
CREATE INDEX IF NOT EXISTS idx_sr_customer_project ON sip_records (customer, project);
CREATE INDEX IF NOT EXISTS idx_sr_chunk_text_fulltext ON sip_records
    USING gin(to_tsvector('simple', COALESCE(chunk_text, '')));

DROP TRIGGER IF EXISTS trg_sip_records_updated_at ON sip_records;
CREATE TRIGGER trg_sip_records_updated_at
    BEFORE UPDATE ON sip_records
    FOR EACH ROW EXECUTE FUNCTION update_updated_at();
