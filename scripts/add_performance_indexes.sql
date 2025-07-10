-- Performance indexes for tag queries optimization
-- Run this when MCP server is stopped: sqlite3 memory.db < add_performance_indexes.sql

-- Critical indexes for tag queries
CREATE INDEX IF NOT EXISTS idx_context_tags_tag_id ON context_tags(tag_id);
CREATE INDEX IF NOT EXISTS idx_context_tags_context_id ON context_tags(context_id);
CREATE INDEX IF NOT EXISTS idx_contexts_created_at ON contexts(created_at);
CREATE INDEX IF NOT EXISTS idx_contexts_project_id ON contexts(project_id);
CREATE INDEX IF NOT EXISTS idx_contexts_project_created ON contexts(project_id, created_at);

-- Composite index for popular tags query optimization
CREATE INDEX IF NOT EXISTS idx_context_tags_composite ON context_tags(tag_id, context_id);

-- List all indexes to verify
.indices contexts
.indices context_tags
.indices tags
