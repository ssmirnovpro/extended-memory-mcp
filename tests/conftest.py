# Extended Memory MCP Server
# Copyright (c) 2024 Sergey Smirnov
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in all
# copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
# SOFTWARE.

"""
Shared pytest fixtures for Memory MCP tests
"""
import pytest
import pytest_asyncio
import asyncio
import tempfile
import os
import sqlite3
from pathlib import Path

# Add project to path
import sys
project_root = Path(__file__).parent.parent / "mcp-server"
sys.path.append(str(project_root))

from extended_memory_mcp.core.memory import MemoryFacade as MemoryManager  # Use new architecture


@pytest.fixture
def temp_test_db():
    """Create temporary test database with proper schema"""
    with tempfile.TemporaryDirectory() as temp_dir:
        db_path = Path(temp_dir) / "test_memory.db"
        
        # Create database with actual normalized schema from init.sql
        conn = sqlite3.connect(str(db_path))
        cursor = conn.cursor()
        
        # Execute the full schema with proper normalized tags structure
        schema_sql = """
        PRAGMA foreign_keys = ON;
        PRAGMA journal_mode = WAL;
        PRAGMA synchronous = NORMAL;

        CREATE TABLE IF NOT EXISTS projects (
            id TEXT PRIMARY KEY,
            name TEXT NOT NULL,
            description TEXT,
            last_accessed TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            status TEXT DEFAULT 'active',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );

        CREATE TABLE IF NOT EXISTS contexts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            project_id TEXT,
            content TEXT NOT NULL,
            importance_level INTEGER NOT NULL CHECK (importance_level BETWEEN 1 AND 10),
            access_count INTEGER DEFAULT 0,
            last_accessed TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            expires_at TIMESTAMP,
            status TEXT DEFAULT 'active'
        );

        CREATE TABLE IF NOT EXISTS tags (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT UNIQUE NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );

        CREATE TABLE IF NOT EXISTS context_tags (
            context_id INTEGER NOT NULL,
            tag_id INTEGER NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            PRIMARY KEY (context_id, tag_id),
            FOREIGN KEY (context_id) REFERENCES contexts(id) ON DELETE CASCADE,
            FOREIGN KEY (tag_id) REFERENCES tags(id) ON DELETE CASCADE
        );

        CREATE INDEX IF NOT EXISTS idx_contexts_project_id ON contexts(project_id);
        CREATE INDEX IF NOT EXISTS idx_contexts_importance ON contexts(importance_level);
        CREATE INDEX IF NOT EXISTS idx_contexts_created_at ON contexts(created_at);
        CREATE INDEX IF NOT EXISTS idx_contexts_status ON contexts(status, expires_at);
        CREATE INDEX IF NOT EXISTS idx_contexts_access ON contexts(access_count, last_accessed);

        CREATE INDEX IF NOT EXISTS idx_tags_name ON tags(name);
        CREATE INDEX IF NOT EXISTS idx_context_tags_context_id ON context_tags(context_id);
        CREATE INDEX IF NOT EXISTS idx_context_tags_tag_id ON context_tags(tag_id);

        INSERT OR IGNORE INTO projects (id, name, description, status) 
        VALUES ('global', 'Global Context', 'Shared context across all projects', 'active');
        """
        
        cursor.executescript(schema_sql)
        conn.commit()
        conn.close()
        
        yield str(db_path)


@pytest.fixture
def temp_config_dir():
    """Create temporary config directory"""
    with tempfile.TemporaryDirectory() as temp_dir:
        config_dir = Path(temp_dir)
        
        # Create memory config
        config_file = config_dir / "memory_config.yaml"
        with open(config_file, 'w') as f:
            f.write("""
retention_policies:
  working_memory_hours: 24
  project_context_months: 6
  critical_decisions_years: 1

importance_thresholds:
  auto_save_threshold: 6
  critical_threshold: 8
  archive_threshold: 3

project_detection:
  auto_detection: true
  confidence_threshold: 0.7
  fallback_project: "general"
""")
        
        yield str(config_dir)


@pytest_asyncio.fixture
async def memory_manager(temp_config_dir, temp_test_db):
    """Create MemoryManager instance with test database"""
    manager = MemoryManager(temp_test_db)
    await manager.initialize_database()
    return manager


@pytest.fixture(scope="function")
def event_loop():
    """Create event loop for async tests with proper cleanup"""
    policy = asyncio.get_event_loop_policy()
    loop = policy.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        yield loop
    finally:
        # Proper cleanup to avoid ResourceWarning
        try:
            # Cancel all running tasks
            pending_tasks = asyncio.all_tasks(loop)
            for task in pending_tasks:
                task.cancel()
            
            # Wait for cancelled tasks to complete
            if pending_tasks:
                loop.run_until_complete(asyncio.gather(*pending_tasks, return_exceptions=True))
        except Exception:
            pass
        
        # Close the loop
        loop.close()


@pytest_asyncio.fixture
async def context_repo(memory_manager):
    """Create ContextRepository instance from MemoryManager for tests"""
    await memory_manager.initialize_database()
    return memory_manager.context_service.context_repo
