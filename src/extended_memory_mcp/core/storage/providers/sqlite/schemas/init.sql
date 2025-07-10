-- Memory MCP Server - Final Database Schema
-- Based on "Dumb Storage, Smart Client" architecture with normalized tags
-- Date: July 2, 2025

PRAGMA foreign_keys = ON;
PRAGMA journal_mode = WAL;
PRAGMA synchronous = NORMAL;

-- Projects table - isolation by project_id
CREATE TABLE IF NOT EXISTS projects (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    description TEXT,
    last_accessed TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    status TEXT DEFAULT 'active',  -- active, archived, completed
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Main contexts table - all Claude-controlled fields (tags field removed)
CREATE TABLE IF NOT EXISTS contexts (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    project_id TEXT,  -- NULL for global contexts
    content TEXT NOT NULL,
    importance_level INTEGER NOT NULL CHECK (importance_level BETWEEN 1 AND 10),  -- Claude rates 1-10
    access_count INTEGER DEFAULT 0,  -- for retention bonus
    last_accessed TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    expires_at TIMESTAMP,  -- calculated by retention policy
    status TEXT DEFAULT 'active'  -- active, archived, expired
);

-- Normalized tags table - each tag stored once
CREATE TABLE IF NOT EXISTS tags (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT UNIQUE NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Many-to-many relationship between contexts and tags
CREATE TABLE IF NOT EXISTS context_tags (
    context_id INTEGER NOT NULL,
    tag_id INTEGER NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (context_id, tag_id),
    FOREIGN KEY (context_id) REFERENCES contexts(id) ON DELETE CASCADE,
    FOREIGN KEY (tag_id) REFERENCES tags(id) ON DELETE CASCADE
);

-- FTS5 virtual table for fast content search (tags removed from FTS as they're now normalized)
CREATE VIRTUAL TABLE IF NOT EXISTS contexts_fts USING fts5(
    content,
    content=contexts,
    content_rowid=id
);

-- Indexes for performance
CREATE INDEX IF NOT EXISTS idx_contexts_project_id ON contexts(project_id);
CREATE INDEX IF NOT EXISTS idx_contexts_importance ON contexts(importance_level);
CREATE INDEX IF NOT EXISTS idx_contexts_created_at ON contexts(created_at);
CREATE INDEX IF NOT EXISTS idx_contexts_status ON contexts(status, expires_at);
CREATE INDEX IF NOT EXISTS idx_contexts_access ON contexts(access_count, last_accessed);

-- Indexes for tags performance
CREATE INDEX IF NOT EXISTS idx_tags_name ON tags(name);
CREATE INDEX IF NOT EXISTS idx_context_tags_context_id ON context_tags(context_id);
CREATE INDEX IF NOT EXISTS idx_context_tags_tag_id ON context_tags(tag_id);

-- Trigger to update FTS5 when contexts table changes
CREATE TRIGGER IF NOT EXISTS contexts_fts_insert AFTER INSERT ON contexts BEGIN
    INSERT INTO contexts_fts(rowid, content) VALUES (new.id, new.content);
END;

CREATE TRIGGER IF NOT EXISTS contexts_fts_delete AFTER DELETE ON contexts BEGIN
    INSERT INTO contexts_fts(contexts_fts, rowid, content) VALUES('delete', old.id, old.content);
END;

CREATE TRIGGER IF NOT EXISTS contexts_fts_update AFTER UPDATE ON contexts BEGIN
    INSERT INTO contexts_fts(contexts_fts, rowid, content) VALUES('delete', old.id, old.content);
    INSERT INTO contexts_fts(rowid, content) VALUES (new.id, new.content);
END;

-- Default global project for cross-project contexts
INSERT OR IGNORE INTO projects (id, name, description, status) 
VALUES ('global', 'Global Context', 'Shared context across all projects', 'active');
