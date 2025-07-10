-- Memory MCP Server Database Schema
-- Schema for storing AI assistant persistent memory

-- User projects table
CREATE TABLE IF NOT EXISTS projects (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    description TEXT,
    last_accessed TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    status TEXT DEFAULT 'active',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Main contexts table (using FTS5 for search)
CREATE VIRTUAL TABLE IF NOT EXISTS contexts_fts USING fts5(
    id UNINDEXED,
    project_id UNINDEXED,
    content,
    importance_level UNINDEXED,
    tags UNINDEXED,
    created_at UNINDEXED,
    expires_at UNINDEXED,
    status UNINDEXED
);

-- Regular contexts table for relational queries
CREATE TABLE IF NOT EXISTS contexts (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    project_id TEXT NOT NULL,
    content TEXT NOT NULL,
    importance_level INTEGER NOT NULL, -- 1-10
    tags TEXT, -- JSON array
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    expires_at TIMESTAMP,
    status TEXT DEFAULT 'active', -- active, archived, expired
    FOREIGN KEY (project_id) REFERENCES projects(id)
);
