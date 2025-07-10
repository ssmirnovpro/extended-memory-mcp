-- Extended schema for architectural decisions
CREATE TABLE IF NOT EXISTS decisions (
    id TEXT PRIMARY KEY,
    project_id TEXT NOT NULL,
    title TEXT NOT NULL,
    description TEXT,
    rationale TEXT,
    implementation_status TEXT DEFAULT 'pending', -- pending, implemented, cancelled, evolved
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (project_id) REFERENCES projects(id)
);

-- Indexes for query optimization
CREATE INDEX IF NOT EXISTS idx_contexts_project ON contexts(project_id);
CREATE INDEX IF NOT EXISTS idx_contexts_importance ON contexts(importance_level);
CREATE INDEX IF NOT EXISTS idx_contexts_created_at ON contexts(created_at);
CREATE INDEX IF NOT EXISTS idx_decisions_project ON decisions(project_id);
CREATE INDEX IF NOT EXISTS idx_decisions_status ON decisions(implementation_status);

-- Trigger for FTS5 table synchronization
CREATE TRIGGER IF NOT EXISTS contexts_ai AFTER INSERT ON contexts BEGIN
  INSERT INTO contexts_fts(id, project_id, content, importance_level, tags, created_at, expires_at, status)
  VALUES (new.id, new.project_id, new.content, new.importance_level, new.tags, new.created_at, new.expires_at, new.status);
END;

CREATE TRIGGER IF NOT EXISTS contexts_au AFTER UPDATE ON contexts BEGIN
  UPDATE contexts_fts SET content = new.content, importance_level = new.importance_level, 
                         tags = new.tags, expires_at = new.expires_at, status = new.status
  WHERE id = new.id;
END;

CREATE TRIGGER IF NOT EXISTS contexts_ad AFTER DELETE ON contexts BEGIN
  DELETE FROM contexts_fts WHERE id = old.id;
END;
