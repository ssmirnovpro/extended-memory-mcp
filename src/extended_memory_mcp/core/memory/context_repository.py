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
Context Repository - Handles all context CRUD operations.

Responsible for:
- Context creation, reading, updating, deletion
- Context querying and filtering
- Access tracking and metrics
"""

import logging
from datetime import datetime
from typing import Any, Dict, List, Optional

import aiosqlite

from .database_manager import DatabaseManager

logger = logging.getLogger(__name__)


class ContextRepository:
    """
    Handles all context-related database operations.
    Simple CRUD without business logic - that stays in services.
    """

    def __init__(self, db_manager: DatabaseManager):
        self.db_manager = db_manager

    async def save_context(
        self,
        content: str,
        importance_level: int,
        project_id: Optional[str] = None,
        tags: Optional[List[str]] = None,
    ) -> Optional[int]:
        """
        Save context to database (Claude controls all parameters)

        Args:
            content: The context content
            importance_level: 1-10, Claude's importance rating
            project_id: Project isolation (None for global)

        Returns:
            Context ID if successful, None if failed
        """
        try:
            # Ensure database is initialized
            await self.db_manager.ensure_database()

            async with self.db_manager.get_connection() as db:
                # Enable foreign keys
                await db.execute("PRAGMA foreign_keys = ON")

                # Insert context without context_type field
                cursor = await db.execute(
                    """
                    INSERT INTO contexts (
                        project_id, content,
                        importance_level, created_at
                    ) VALUES (?, ?, ?, ?)
                """,
                    (
                        project_id,
                        content,
                        importance_level,
                        datetime.now().isoformat(),
                    ),
                )

                context_id = cursor.lastrowid
                await db.commit()

                logger.info(f"Saved context {context_id} for project {project_id}")
                return context_id

        except Exception as e:
            logger.error(f"Failed to save context: {e}")
            return None

    async def load_contexts(
        self,
        project_id: Optional[str] = None,
        importance_min: int = 7,
        limit: int = 50,
        offset: int = 0,
    ) -> List[Dict[str, Any]]:
        """
        Load contexts with filtering (Claude-controlled parameters)

        Args:
            project_id: Filter by project (None for all projects)
            importance_min: Minimum importance level (default: 7)
            limit: Maximum number of contexts to return
            offset: Skip this many contexts (pagination)

        Returns:
            List of context dictionaries sorted chronologically (newest first, returned oldest first)
        """
        try:
            await self.db_manager.ensure_database()

            async with self.db_manager.get_connection() as db:
                # Build dynamic query
                where_conditions = ["importance_level >= ?"]
                params = [importance_min]

                if project_id is not None:
                    where_conditions.append("project_id = ?")
                    params.append(project_id)

                where_clause = " AND ".join(where_conditions)
                params.extend([limit, offset])

                # Build the complete query safely - search newest first, return oldest first
                query = (
                    """
                    SELECT id, project_id, content,
                           importance_level, status, created_at,
                           expires_at
                    FROM contexts
                    WHERE """
                    + where_clause
                    + """
                    ORDER BY created_at DESC, id DESC
                    LIMIT ? OFFSET ?
                """
                )

                cursor = await db.execute(query, params)

                rows = await cursor.fetchall()

                contexts = []
                for row in rows:
                    context = {
                        "id": row[0],
                        "project_id": row[1],
                        "content": row[2],
                        "importance_level": row[3],
                        "status": row[4],
                        "created_at": row[5],
                        "expires_at": row[6],
                    }
                    contexts.append(context)

                return contexts

        except Exception as e:
            logger.error(f"Failed to load contexts: {e}")
            return []

    async def get_context_by_id(self, context_id: int) -> Optional[Dict[str, Any]]:
        """Get single context by ID"""
        try:
            async with self.db_manager.get_connection() as db:
                cursor = await db.execute(
                    """
                    SELECT id, project_id, content,
                           importance_level, status, created_at,
                           expires_at
                    FROM contexts WHERE id = ?
                """,
                    (context_id,),
                )

                row = await cursor.fetchone()
                if not row:
                    return None

                return {
                    "id": row[0],
                    "project_id": row[1],
                    "content": row[2],
                    "importance_level": row[3],
                    "status": row[4],
                    "created_at": row[5],
                    "expires_at": row[6],
                }

        except Exception as e:
            logger.error(f"Failed to get context {context_id}: {e}")
            return None

    async def delete_context(self, context_id: int) -> bool:
        """Delete context by ID (Claude decides what to forget)"""
        try:
            async with self.db_manager.get_connection() as db:
                # Enable foreign keys for cascade delete
                await db.execute("PRAGMA foreign_keys = ON")

                cursor = await db.execute(
                    """
                    DELETE FROM contexts WHERE id = ?
                """,
                    (context_id,),
                )

                await db.commit()

                if cursor.rowcount > 0:
                    logger.info(f"Deleted context {context_id}")
                    return True
                else:
                    logger.warning(f"Context {context_id} not found for deletion")
                    return False

        except Exception as e:
            logger.error(f"Failed to delete context {context_id}: {e}")
            return False

    async def count_contexts(self, project_id: Optional[str] = None) -> int:
        """Count total contexts, optionally filtered by project"""
        try:
            async with self.db_manager.get_connection() as db:
                if project_id is not None:
                    cursor = await db.execute(
                        """
                        SELECT COUNT(*) FROM contexts WHERE project_id = ?
                    """,
                        (project_id,),
                    )
                else:
                    cursor = await db.execute("SELECT COUNT(*) FROM contexts")

                row = await cursor.fetchone()
                return row[0] if row else 0

        except Exception as e:
            logger.error(f"Failed to count contexts: {e}")
            return 0

    async def get_contexts_by_importance(
        self, min_importance: int = 7, limit: int = 30
    ) -> List[Dict[str, Any]]:
        """Load high-importance contexts across all projects"""
        try:
            async with self.db_manager.get_connection() as db:
                cursor = await db.execute(
                    """
                    SELECT id, project_id, content,
                           importance_level, status, created_at
                    FROM contexts
                    WHERE importance_level >= ? AND status = 'active'
                    ORDER BY created_at DESC
                    LIMIT ?
                """,
                    (min_importance, limit),
                )

                rows = await cursor.fetchall()

                contexts = []
                for row in rows:
                    context = {
                        "id": row[0],
                        "project_id": row[1],
                        "content": row[2],
                        "importance_level": row[3],
                        "status": row[4],
                        "created_at": row[5],
                    }
                    contexts.append(context)

                return contexts

        except Exception as e:
            logger.error(f"Failed to load high importance contexts: {e}")
            return []

    async def load_contexts_by_ids(self, context_ids: List[int]) -> List[Dict[str, Any]]:
        """
        Load contexts by specific IDs using optimized SQL WHERE IN clause.
        This replaces inefficient Python filtering.

        Args:
            context_ids: List of context IDs to load

        Returns:
            List of context dictionaries (only found contexts)
        """
        try:
            if not context_ids:
                return []

            await self.db_manager.ensure_database()

            async with self.db_manager.get_connection() as db:
                # Create placeholders for IN clause
                placeholders = ",".join("?" * len(context_ids))

                query = (
                    """
                    SELECT id, project_id, content,
                           importance_level, status, created_at,
                           expires_at
                    FROM contexts
                    WHERE id IN ("""
                    + placeholders
                    + """)
                    ORDER BY created_at DESC
                """
                )

                cursor = await db.execute(query, context_ids)
                rows = await cursor.fetchall()

                contexts = []
                for row in rows:
                    context = {
                        "id": row[0],
                        "project_id": row[1],
                        "content": row[2],
                        "importance_level": row[3],
                        "status": row[4],
                        "created_at": row[5],
                        "expires_at": row[6],
                    }
                    contexts.append(context)

                return contexts

        except Exception as e:
            logger.error(f"Failed to load contexts by IDs: {e}")
            return []

    async def search_contexts_optimized(
        self,
        project_id: Optional[str] = None,
        importance_min: int = 1,
        content_search: Optional[str] = None,
        limit: int = 100,
        offset: int = 0,
    ) -> List[Dict[str, Any]]:
        """
        Search contexts with SQL-based filtering to avoid N+1 and Python filtering issues.

        Args:
            project_id: Filter by project (None for all projects)
            importance_min: Minimum importance level
            content_search: Search term in content (SQL LIKE)
            limit: Maximum number of contexts to return
            offset: Skip this many contexts (pagination)

        Returns:
            List of context dictionaries with SQL-optimized filtering
        """
        try:
            await self.db_manager.ensure_database()

            async with self.db_manager.get_connection() as db:
                # Build dynamic query with SQL-based filtering
                where_conditions = ["importance_level >= ?"]
                params = [importance_min]

                if project_id is not None:
                    where_conditions.append("project_id = ?")
                    params.append(project_id)

                # SQL-based content search (RESERVED: for future advanced search features)
                if content_search:
                    where_conditions.append("content LIKE ?")
                    params.append(f"%{content_search}%")

                where_clause = " AND ".join(where_conditions)
                params.extend([limit, offset])

                # Build the complete query with SQL filtering
                query = (
                    """
                    SELECT id, project_id, content,
                           importance_level, status, created_at,
                           expires_at
                    FROM contexts
                    WHERE """
                    + where_clause
                    + """
                    ORDER BY created_at DESC
                    LIMIT ? OFFSET ?
                """
                )

                cursor = await db.execute(query, params)
                rows = await cursor.fetchall()

                contexts = []
                for row in rows:
                    context = {
                        "id": row[0],
                        "project_id": row[1],
                        "content": row[2],
                        "importance_level": row[3],
                        "status": row[4],
                        "created_at": row[5],
                        "expires_at": row[6],
                    }
                    contexts.append(context)

                return contexts

        except Exception as e:
            logger.error(f"Failed to search contexts optimized: {e}")
            return []
