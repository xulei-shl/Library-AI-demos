-- ============================================================================
-- 图书向量化数据库迁移脚本
-- 用途: 为 books 表添加向量化状态追踪字段
-- 执行方式: sqlite3 books_history.db < scripts/migrate_add_embedding_fields.sql
-- ============================================================================

-- 新增字段
ALTER TABLE books ADD COLUMN embedding_id TEXT;
ALTER TABLE books ADD COLUMN embedding_status TEXT DEFAULT 'pending';
ALTER TABLE books ADD COLUMN embedding_date DATETIME;
ALTER TABLE books ADD COLUMN embedding_error TEXT;
ALTER TABLE books ADD COLUMN retry_count INTEGER DEFAULT 0;

-- 创建索引，加速增量查询
CREATE INDEX IF NOT EXISTS idx_embedding_status ON books(embedding_status);
CREATE INDEX IF NOT EXISTS idx_retry_count ON books(retry_count);

-- 验证字段是否添加成功
SELECT 
    name,
    type,
    dflt_value
FROM pragma_table_info('books')
WHERE name LIKE 'embedding%' OR name = 'retry_count';
