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
SQLite Storage Provider - Wrapper around existing DatabaseManager and repositories.

Implements IStorageProvider interface using current SQLite-based architecture.
This maintains backward compatibility while enabling storage abstraction.
"""

import logging
from datetime import datetime
from typing import Any, Dict, List, Optional

# Module-level logger
import aiosqlite

from extended_memory_mcp.storage_types.storage_types import (
    ContextData,
    ContextList,
    InitContextsResult,
    PopularTag,
    ProjectInfo,
    ProjectList,
    SearchFilters,
    StorageStats,
    TagList,
)

from ....errors import MemoryMCPError, StorageError, ValidationError, error_handler
from ...interfaces.storage_provider import IStorageProvider

logger = logging.getLogger(__name__)


class SQLiteStorageProvider(IStorageProvider):
    """
    Repository-based SQLite implementation of storage provider.

    Uses direct repository access for optimal performance and clean architecture.
    Maintains full backward compatibility with current system.
    """

    def __init__(
        self, db_path: Optional[str] = None, timeout: float = 30.0, check_same_thread: bool = True
    ):
        """
        Initialize SQLite storage provider.

        Args:
            db_path: Database file path (None for auto-location)
            timeout: Connection timeout in seconds
            check_same_thread: SQLite check_same_thread parameter
        """
        # Import memory components locally to avoid circular dependencies
        from ....memory.context_repository import ContextRepository
        from ....memory.database_manager import DatabaseManager
        from ....memory.instruction_service import InstructionService

        # Personality service removed - functionality deleted
        from ....memory.tags_repository import TagsRepository

        self.db_manager = DatabaseManager(db_path)
        self.context_repo = ContextRepository(self.db_manager)
        self.tags_repo = TagsRepository(self.db_manager)

        # High-level services for complex operations
        self.instruction_service = InstructionService(
            self.context_repo, self.tags_repo  # Personality service removed
        )

        # Store connection parameters for potential future use
        self.timeout = timeout
        self.check_same_thread = check_same_thread

        # Store database path
        self._db_path = db_path

    async def initialize(self) -> bool:
        """Initialize SQLite database and tables."""
        try:
            await self.db_manager.ensure_database()

            # Create performance indexes for scalability
            await self._create_performance_indexes()

            return True
        except Exception as e:
            # Use structured error handling
            storage_error = error_handler.handle_error(
                e,
                context={"database_path": self._db_path},
                operation="sqlite_database_initialization",
            )
            return False

    async def health_check(self) -> bool:
        """Check SQLite database health."""
        try:
            async with self.db_manager.get_connection() as db:
                await db.execute("SELECT 1")
                return True
        except Exception as e:
            # Log health check failure but don't crash
            error_handler.handle_error(
                e, context={"database_path": self._db_path}, operation="sqlite_health_check"
            )
            return False

    async def save_context(
        self,
        content: str,
        importance_level: int,
        project_id: Optional[str] = None,
        tags: Optional[List[str]] = None,
    ) -> Optional[str]:
        """Save context using existing ContextRepository."""
        try:
            # Use existing repository method
            context_id = await self.context_repo.save_context(
                content=content,
                importance_level=importance_level,
                project_id=project_id,
            )

            if context_id and tags:
                # Add tags using TagsRepository
                await self.tags_repo.save_context_tags(context_id, tags)

            return str(context_id) if context_id else None

        except Exception as e:
            # Structured error handling for context saving
            storage_error = error_handler.handle_error(
                e,
                context={
                    "content_length": len(content),
                    "importance_level": importance_level,
                    "project_id": project_id,
                    "tags_count": len(tags) if tags else 0,
                },
                operation="save_context_sqlite",
            )
            return None

    async def load_contexts(
        self,
        project_id: Optional[str] = None,
        limit: int = 50,
        importance_threshold: int = 1,  # Match Redis default
        tags_filter: Optional[List[str]] = None,
    ) -> ContextList:
        """Load contexts using existing ContextRepository with optimized batch tag loading."""
        try:
            if tags_filter:
                # Use tag-based filtering when tags_filter is provided
                context_ids = await self.tags_repo.find_contexts_by_multiple_tags(
                    tags=tags_filter, limit=limit, project_id=project_id
                )

                if not context_ids:
                    return []

                # Convert to strings for load_contexts_by_ids (which handles batch tag loading)
                context_id_strings = [str(cid) for cid in context_ids]
                contexts = await self.load_contexts_by_ids(context_id_strings)

                # Filter by importance threshold
                filtered_contexts = [
                    ctx
                    for ctx in contexts
                    if ctx.get("importance_level", 0) >= importance_threshold
                ]

                # Sort by creation time (newest first) and limit
                filtered_contexts.sort(key=lambda x: x.get("created_at", ""), reverse=True)

                return filtered_contexts[:limit]
            else:
                # Use existing repository method without tag filtering
                contexts = await self.context_repo.load_contexts(
                    project_id=project_id,
                    limit=limit,
                    importance_min=importance_threshold,
                )

                # Load tags for ALL contexts in a single batch query (fixes N+1)
                if contexts:
                    context_ids_for_tags = [ctx["id"] for ctx in contexts]
                    tags_batch = await self.tags_repo.load_context_tags_batch(context_ids_for_tags)

                    # Attach tags to contexts
                    for context in contexts:
                        context_id = context["id"]
                        context["tags"] = tags_batch.get(context_id, [])

                return contexts

        except Exception as e:
            # Structured error handling for context loading
            storage_error = error_handler.handle_error(
                e,
                context={
                    "project_id": project_id,
                    "limit": limit,
                    "importance_threshold": importance_threshold,
                    "tags_filter": tags_filter,
                },
                operation="load_contexts_sqlite",
            )
            return []

    async def load_contexts_by_ids(self, context_ids: List[str]) -> ContextList:
        """
        Load specific contexts by their IDs using optimized batch queries.
        Fixed N+1 problem by loading all tags in a single batch query.
        """
        try:
            if not context_ids:
                return []

            # Convert string IDs to integers for existing repository
            int_ids = []
            for context_id in context_ids:
                try:
                    int_ids.append(int(context_id))
                except ValueError:
                    continue  # Skip invalid IDs

            if not int_ids:
                return []

            # Use optimized SQL query through repository
            contexts = await self.context_repo.load_contexts_by_ids(int_ids)

            # Load tags for ALL contexts in a single batch query (fixes N+1)
            if contexts:
                context_ids_for_tags = [ctx["id"] for ctx in contexts]
                tags_batch = await self.tags_repo.load_context_tags_batch(context_ids_for_tags)

                # Attach tags to contexts
                for context in contexts:
                    context_id = context["id"]
                    context["tags"] = tags_batch.get(context_id, [])

            return contexts

        except Exception as e:
            storage_error = error_handler.handle_error(
                e, context={"context_ids": context_ids}, operation="load_contexts_by_ids_sqlite"
            )
            return []

    async def delete_context(self, context_id: str) -> bool:
        """Delete context using existing ContextRepository."""
        try:
            # Convert string ID to int for existing API
            int_context_id = int(context_id)
            return await self.context_repo.delete_context(int_context_id)
        except Exception as e:
            logger.error(f"Error deleting context from SQLite: {e}")
            return False

    async def update_context(
        self, context_id: str, content: Optional[str] = None, importance_level: Optional[int] = None
    ) -> bool:
        """Update context using existing ContextRepository."""
        try:
            int_context_id = int(context_id)
            return await self.context_repo.update_context(
                context_id=int_context_id, content=content, importance_level=importance_level
            )
        except Exception as e:
            logger.error(f"Error updating context in SQLite: {e}")
            return False

    async def list_all_projects_global(self) -> ProjectList:
        """List ALL projects globally from contexts table."""
        try:
            # Simple query: get distinct project_ids from contexts
            # Redis-compatible approach - no complex JOINs
            async with aiosqlite.connect(self.db_manager.db_path) as db:
                async with db.execute(
                    "SELECT DISTINCT project_id, COUNT(*) as context_count FROM contexts WHERE project_id IS NOT NULL GROUP BY project_id"
                ) as cursor:
                    rows = await cursor.fetchall()

                    projects = []
                    for row in rows:
                        projects.append(
                            {
                                "id": row[0],
                                "name": row[0],  # project_id as name
                                "context_count": row[1],
                            }
                        )

                    return projects
        except Exception as e:
            logger.error(f"Error listing all projects globally from SQLite: {e}")
            return []

    async def load_context(self, context_id: str) -> Optional[ContextData]:
        """Load single context by ID with tags using optimized batch method for consistency."""
        try:
            int_context_id = int(context_id)
            context = await self.context_repo.get_context_by_id(int_context_id)

            if context:
                # Use batch method for consistency (even for single context)
                tags_batch = await self.tags_repo.load_context_tags_batch([int_context_id])
                context["tags"] = tags_batch.get(int_context_id, [])

            return context
        except Exception as e:
            logger.error(f"Error loading context {context_id}: {e}")
            return None

    async def search_contexts(self, filters: SearchFilters) -> ContextList:
        """Search contexts with complex filters using optimized SQL queries."""
        try:
            # Extract filters
            project_id = filters.get("project_id")
            min_importance = filters.get("min_importance", 1)
            tags_filter = filters.get("tags", [])
            content_search = filters.get(
                "content_search"
            )  # RESERVED: for future advanced search features
            limit = filters.get("limit", 100)

            if tags_filter:
                # Tag-based search: first find contexts by tags, then apply other filters
                context_ids = await self.tags_repo.find_contexts_by_multiple_tags(
                    tags=tags_filter,
                    limit=limit * 2,  # Get more candidates for filtering
                    project_id=project_id,
                )

                if not context_ids:
                    return []

                # Load contexts by IDs with optimized batch query
                contexts = await self.context_repo.load_contexts_by_ids(context_ids)

                # Apply additional filters in memory (already loaded contexts)
                filtered_contexts = []
                for context in contexts:
                    # Importance filter
                    if context.get("importance_level", 0) < min_importance:
                        continue

                    # Content search filter
                    if (
                        content_search
                        and content_search.lower() not in context.get("content", "").lower()
                    ):
                        continue

                    filtered_contexts.append(context)

                # Load tags for all filtered contexts in one batch
                if filtered_contexts:
                    context_ids_for_tags = [ctx["id"] for ctx in filtered_contexts]
                    tags_batch = await self.tags_repo.load_context_tags_batch(context_ids_for_tags)

                    # Attach tags to contexts
                    for context in filtered_contexts:
                        context_id = context["id"]
                        context["tags"] = tags_batch.get(context_id, [])

                # Sort and limit final results
                filtered_contexts.sort(
                    key=lambda x: (x.get("importance_level", 0), x.get("created_at", "")),
                    reverse=True,
                )

                return filtered_contexts[:limit]
            else:
                # No tag filtering: use optimized context search with SQL filtering
                contexts = await self.context_repo.search_contexts_optimized(
                    project_id=project_id,
                    importance_min=min_importance,
                    content_search=content_search,
                    limit=limit,
                )

                # Load tags for all contexts in one batch query
                if contexts:
                    context_ids = [ctx["id"] for ctx in contexts]
                    tags_batch = await self.tags_repo.load_context_tags_batch(context_ids)

                    # Attach tags to contexts
                    for context in contexts:
                        context_id = context["id"]
                        context["tags"] = tags_batch.get(context_id, [])

                return contexts

        except Exception as e:
            logger.error(f"Error searching contexts: {e}")
            return []

    async def get_context_tags(self, context_id: str) -> List[str]:
        """Get tags for context using existing TagsRepository."""
        try:
            int_context_id = int(context_id)
            return await self.tags_repo.load_context_tags(int_context_id)
        except Exception as e:

            logger.error(f"Error getting context tags from SQLite: {e}")
            return []

    async def add_context_tag(self, context_id: str, tag: str) -> bool:
        """Add tag to context using existing TagsRepository."""
        try:
            int_context_id = int(context_id)
            await self.tags_repo.save_context_tags(int_context_id, [tag])
            return True
        except Exception as e:

            logger.error(f"Error adding tag to context in SQLite: {e}")
            return False

    async def find_contexts_by_multiple_tags(
        self, tags: List[str], project_id: Optional[str] = None, limit: int = 50
    ) -> ContextList:
        """
        Find contexts that have any of the specified tags (OR logic).

        Args:
            tags: List of tag names to search for
            project_id: Filter by project (None for all projects)
            limit: Maximum number of contexts to return

        Returns:
            List of ContextData that match any of the tags
        """
        try:
            # Use TagsRepository to find contexts by multiple tags
            context_ids = await self.tags_repo.find_contexts_by_multiple_tags(
                tags=tags, project_id=project_id, limit=limit
            )

            # Convert int IDs to strings and load contexts
            str_context_ids = [str(cid) for cid in context_ids]
            return await self.load_contexts_by_ids(str_context_ids)

        except Exception as e:
            logger.error(f"Error finding contexts by multiple tags in SQLite: {e}")
            return []

    async def get_popular_tags(
        self, limit: int = 10, min_usage: int = 2, project_id: Optional[str] = None
    ) -> TagList:
        """Get popular tags using existing TagsRepository."""
        try:
            return await self.tags_repo.get_popular_tags(
                limit=limit, min_usage=min_usage, project_id=project_id
            )
        except Exception as e:
            logger.error(f"Error getting popular tags from SQLite: {e}")
            return []

    async def get_storage_stats(self) -> StorageStats:
        """Get SQLite storage statistics."""
        try:
            async with self.db_manager.get_connection() as db:
                # Count contexts
                cursor = await db.execute("SELECT COUNT(*) FROM contexts")
                context_count = (await cursor.fetchone())[0]

                # Count projects
                cursor = await db.execute("SELECT COUNT(*) FROM projects")
                project_count = (await cursor.fetchone())[0]

                # Database file size
                import os

                db_size = (
                    os.path.getsize(self.db_manager.db_path)
                    if os.path.exists(self.db_manager.db_path)
                    else 0
                )

                return {
                    "provider": "sqlite",
                    "total_contexts": context_count,
                    "total_projects": project_count,
                    "database_size_bytes": db_size,
                    "database_path": self.db_manager.db_path,
                }

        except Exception as e:

            logger.error(f"Error getting SQLite storage stats: {e}")
            return {"provider": "sqlite", "error": str(e)}

    async def cleanup_expired(self) -> int:
        """Clean up expired contexts in SQLite."""
        try:
            # Implement cleanup logic based on retention policies
            # For now, return 0 (no automatic cleanup)
            return 0
        except Exception as e:

            logger.error(f"Error in SQLite cleanup: {e}")
            return 0

    async def forget_context(self, context_id: str) -> bool:
        """
        Delete a context by ID (alias for delete_context to match server.py expectations).
        """
        return await self.delete_context(context_id)

    async def load_init_contexts(
        self, project_id: Optional[str] = None, limit: int = 30
    ) -> InitContextsResult:
        """
        Load contexts for session initialization with instruction and personality.

        Delegates to InstructionService for proper formatting.
        """
        try:
            return await self.instruction_service.load_init_contexts(project_id, limit)
        except Exception as e:

            logger.error(f"Error loading init contexts from SQLite: {e}")
            return {
                "init_instruction": "",
                "contexts": [],
                "metadata": {
                    "project_id": project_id,
                    "context_count": 0,
                    "timestamp": datetime.now().isoformat(),
                    "error": str(e),
                },
            }

    async def load_high_importance_contexts(self, limit: int = 5) -> List[Dict[str, Any]]:
        """
        Load high-importance contexts across all projects.
        Required by server.py for startup context resource.
        """
        try:
            return await self.instruction_service.load_smart_contexts(
                project_id=None, limit=limit  # All projects
            )
        except Exception as e:

            logger.error(f"Error loading high importance contexts: {e}")
            return []

    async def _create_performance_indexes(self) -> None:
        """
        Create performance indexes for scalability.
        Called during initialization to ensure optimal query performance.
        """
        indexes = [
            # Core context indexes for fast filtering
            "CREATE INDEX IF NOT EXISTS idx_contexts_project_created ON contexts(project_id, created_at DESC)",
            "CREATE INDEX IF NOT EXISTS idx_contexts_project_importance ON contexts(project_id, importance_level)",
            "CREATE INDEX IF NOT EXISTS idx_contexts_importance ON contexts(importance_level)",
            "CREATE INDEX IF NOT EXISTS idx_contexts_created_at ON contexts(created_at)",
            # Tag relationship indexes for JOIN optimization
            "CREATE INDEX IF NOT EXISTS idx_context_tags_tag_id ON context_tags(tag_id)",
            "CREATE INDEX IF NOT EXISTS idx_context_tags_context_id ON context_tags(context_id)",
            "CREATE INDEX IF NOT EXISTS idx_context_tags_composite ON context_tags(tag_id, context_id)",
            # Tag lookup indexes
            "CREATE INDEX IF NOT EXISTS idx_tags_name ON tags(name)",
            # Project isolation indexes
            "CREATE INDEX IF NOT EXISTS idx_contexts_project_id ON contexts(project_id)",
        ]

        try:
            import aiosqlite

            async with aiosqlite.connect(self.db_manager.db_path) as db:
                for index_sql in indexes:
                    await db.execute(index_sql)
                await db.commit()

            logger.info(f"Created {len(indexes)} performance indexes for SQLite scalability")

        except Exception as e:
            logger.warning(f"Failed to create some performance indexes: {e}")
            # Non-critical - continue initialization

    async def close(self) -> None:
        """Close SQLite connections (no persistent connections to close)."""
        # SQLite connections are auto-closed in context managers
        pass
