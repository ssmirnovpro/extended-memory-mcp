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
Database Manager - Handles database connection and initialization.

Responsible for:
- Database path management
- Schema initialization
- Connection handling
"""

import logging
import os
from pathlib import Path
from typing import Optional

import aiosqlite

logger = logging.getLogger(__name__)


class DatabaseManager:
    """
    Manages database connection and initialization.
    Follows "Simple Storage" pattern - no business logic here.
    """

    def __init__(self, db_path: Optional[str] = None):
        self.db_path = db_path or self._get_default_db_path()
        self._ensure_db_directory()

    def _get_default_db_path(self) -> str:
        """
        Get default database path from STORAGE_CONNECTION_STRING config with fallback
        """
        from ..config import get_env_default

        # Get default connection string from STORAGE_CONNECTION_STRING env/config
        default_connection = get_env_default(
            "STORAGE_CONNECTION_STRING", "sqlite:///~/.local/share/extended-memory-mcp/memory.db"
        )

        # Extract path from connection string or treat as path
        if default_connection.startswith("sqlite:///"):
            default_path = default_connection[10:]  # Remove 'sqlite:///'
        else:
            default_path = default_connection

        # Expand the path
        expanded_path = os.path.expanduser(default_path)

        # Ensure directory exists
        default_dir = os.path.dirname(expanded_path)
        os.makedirs(default_dir, exist_ok=True)

        return expanded_path

    def _ensure_db_directory(self):
        """Ensure database directory exists"""
        db_dir = Path(self.db_path).parent
        db_dir.mkdir(parents=True, exist_ok=True)

    async def ensure_database(self) -> bool:
        """Ensure database is initialized (lazy initialization)"""
        # Check if database exists and has tables
        try:
            async with aiosqlite.connect(self.db_path) as db:
                cursor = await db.execute(
                    "SELECT name FROM sqlite_master WHERE type='table' AND name='contexts'"
                )
                result = await cursor.fetchone()
                if not result:
                    # Database exists but no tables, initialize
                    return await self.initialize_database()
                return True
        except Exception:
            # Database might not exist, initialize it
            return await self.initialize_database()

    async def initialize_database(self) -> bool:
        """
        Initialize database with schema if not exists.
        Returns True if successful, False otherwise.
        """
        try:
            async with aiosqlite.connect(self.db_path) as db:
                # Create normalized schema with proper constraints (context_type removed)
                await db.execute(
                    """
                    CREATE TABLE IF NOT EXISTS contexts (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        project_id TEXT,
                        content TEXT NOT NULL,
                        importance_level INTEGER NOT NULL,
                        status TEXT DEFAULT 'active',
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        expires_at TIMESTAMP,
                        access_count INTEGER DEFAULT 0,
                        last_accessed TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    )
                """
                )

                # Normalized tags schema
                await db.execute(
                    """
                    CREATE TABLE IF NOT EXISTS tags (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        name TEXT UNIQUE NOT NULL
                    )
                """
                )

                await db.execute(
                    """
                    CREATE TABLE IF NOT EXISTS context_tags (
                        context_id INTEGER,
                        tag_id INTEGER,
                        PRIMARY KEY (context_id, tag_id),
                        FOREIGN KEY (context_id) REFERENCES contexts(id) ON DELETE CASCADE,
                        FOREIGN KEY (tag_id) REFERENCES tags(id) ON DELETE CASCADE
                    )
                """
                )

                # Projects table
                await db.execute(
                    """
                    CREATE TABLE IF NOT EXISTS projects (
                        id TEXT PRIMARY KEY,
                        name TEXT NOT NULL,
                        description TEXT,
                        last_accessed TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        status TEXT DEFAULT 'active'
                    )
                """
                )

                # Create indexes for performance
                await db.execute(
                    "CREATE INDEX IF NOT EXISTS idx_contexts_project_id ON contexts(project_id)"
                )
                await db.execute(
                    "CREATE INDEX IF NOT EXISTS idx_contexts_importance ON contexts(importance_level)"
                )
                await db.execute(
                    "CREATE INDEX IF NOT EXISTS idx_contexts_created_at ON contexts(created_at)"
                )
                await db.execute("CREATE INDEX IF NOT EXISTS idx_tags_name ON tags(name)")

                await db.commit()
                logger.info(f"Database initialized at {self.db_path}")
                return True

        except Exception as e:
            logger.error(f"Failed to initialize database: {e}")
            return False

    def get_connection(self):
        """Get database connection context manager"""
        return aiosqlite.connect(self.db_path)
