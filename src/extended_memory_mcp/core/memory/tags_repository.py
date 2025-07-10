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
Tags Repository - Handles all tag-related database operations.

Responsible for:
- Tag creation and management
- Context-tag relationships
- Tag-based querying
"""

import logging
from typing import Any, Dict, List, Optional

import aiosqlite

from .database_manager import DatabaseManager


# Default tags configuration
def get_default_tags_config():
    return {
        "popular_tags_limit": 10,
        "popular_tags_min_usage": 2,
        "show_in_responses": True,
        "recent_tags_hours": 24,
        "smart_grouping_popular_threshold": 3,
        "smart_grouping_recent_threshold": 1,
    }


logger = logging.getLogger(__name__)


class TagsRepository:
    """
    Handles all tag-related database operations.
    Uses normalized tags schema for efficient querying.
    """

    def __init__(self, db_manager: DatabaseManager):
        self.db_manager = db_manager

    async def save_context_tags(self, context_id: int, tags: List[str]) -> bool:
        """Save tags for a context using normalized schema"""
        try:
            async with self.db_manager.get_connection() as db:
                for tag_name in tags:
                    if not isinstance(tag_name, str) or not tag_name.strip():
                        continue

                    tag_name = tag_name.strip().lower()

                    # Insert tag if not exists
                    await db.execute(
                        """
                        INSERT OR IGNORE INTO tags (name) VALUES (?)
                    """,
                        (tag_name,),
                    )

                    # Get tag ID
                    cursor = await db.execute("SELECT id FROM tags WHERE name = ?", (tag_name,))
                    tag_row = await cursor.fetchone()
                    if tag_row:
                        tag_id = tag_row[0]

                        # Link context to tag
                        await db.execute(
                            """
                            INSERT OR IGNORE INTO context_tags (context_id, tag_id)
                            VALUES (?, ?)
                        """,
                            (context_id, tag_id),
                        )

                await db.commit()
                return True

        except Exception as e:
            logger.error(f"Failed to save context tags: {e}")
            return False

    async def load_context_tags(self, context_id: int) -> List[str]:
        """Load tags for a specific context"""
        try:
            async with self.db_manager.get_connection() as db:
                cursor = await db.execute(
                    """
                    SELECT t.name FROM tags t
                    JOIN context_tags ct ON t.id = ct.tag_id
                    WHERE ct.context_id = ?
                    ORDER BY t.name
                """,
                    (context_id,),
                )

                rows = await cursor.fetchall()
                return [row[0] for row in rows]

        except Exception as e:
            logger.error(f"Failed to load tags for context {context_id}: {e}")
            return []

    def _load_config(self) -> Dict[str, Any]:
        """Load config using centralized config utils"""
        return get_default_tags_config()

    async def get_popular_tags(
        self,
        limit: Optional[int] = None,
        min_usage: Optional[int] = None,
        recent_hours: Optional[int] = None,
        project_id: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """
        Get popular tags and recent tags with usage count, optionally filtered by project

        Args:
            limit: Maximum number of tags to return (default: from config)
            min_usage: Minimum usage count for popular tags (default: from config)
            recent_hours: Hours to consider for recent tags (default: from config)
            project_id: Project ID to filter tags by (optional, returns all projects if None)

        Returns:
            List of dicts with 'tag' and 'count' keys, sorted by usage count desc

        Note:
            - If project_id is provided, only returns tags used in that project
            - Uses JOIN with contexts table to enable project-based filtering
            - Returns combination of popular tags (≥min_usage) and recent tags (1 use, within recent_hours)
        """
        try:
            import time

            start_time = time.time()

            # Load settings from config if not provided
            config = self._load_config()
            if limit is None:
                limit = config.get("tags", {}).get("popular_tags_limit", 10)
            if min_usage is None:
                min_usage = config.get("tags", {}).get("popular_tags_min_usage", 2)
            if recent_hours is None:
                recent_hours = config.get("tags", {}).get("recent_tags_hours", 24)

            async with self.db_manager.get_connection() as db:
                # Build query with optional project_id filter
                if project_id is not None:
                    # Filter by project_id
                    query = """
                        SELECT t.name, COUNT(ct.context_id) as usage_count, MAX(c.created_at) as latest_use
                        FROM tags t
                        JOIN context_tags ct ON t.id = ct.tag_id
                        JOIN contexts c ON ct.context_id = c.id
                        WHERE c.project_id = ?
                        GROUP BY t.id, t.name
                        HAVING
                            usage_count >= ?
                            OR (usage_count = 1 AND datetime(latest_use) > datetime('now', '-' || ? || ' hours'))
                        ORDER BY usage_count DESC, latest_use DESC
                        LIMIT ?
                    """
                    cursor = await db.execute(
                        query,
                        (project_id, min_usage, recent_hours, limit),
                    )
                else:
                    # Original query without project filter
                    query = """
                        SELECT t.name, COUNT(ct.context_id) as usage_count, MAX(c.created_at) as latest_use
                        FROM tags t
                        JOIN context_tags ct ON t.id = ct.tag_id
                        JOIN contexts c ON ct.context_id = c.id
                        GROUP BY t.id, t.name
                        HAVING
                            usage_count >= ?
                            OR (usage_count = 1 AND datetime(latest_use) > datetime('now', '-' || ? || ' hours'))
                        ORDER BY usage_count DESC, latest_use DESC
                        LIMIT ?
                    """
                    cursor = await db.execute(
                        query,
                        (min_usage, recent_hours, limit),
                    )

                rows = await cursor.fetchall()
                result = [{"tag": row[0], "count": row[1]} for row in rows]

                # Log performance metrics
                elapsed_time = time.time() - start_time
                logger.info(
                    f"get_popular_tags executed in {elapsed_time:.3f}s - returned {len(result)} tags (project_id={project_id})"
                )

                return result

        except Exception as e:
            logger.error(f"Failed to get popular tags: {e}")
            return []

    async def find_contexts_by_tag(
        self, tag_name: str, limit: int = 50, project_id: Optional[str] = None
    ) -> List[int]:
        """Find context IDs that have a specific tag, optionally filtered by project"""
        try:
            async with self.db_manager.get_connection() as db:
                if project_id is not None:
                    # Filter by both tag and project_id
                    cursor = await db.execute(
                        """
                        SELECT ct.context_id FROM context_tags ct
                        JOIN tags t ON ct.tag_id = t.id
                        JOIN contexts c ON ct.context_id = c.id
                        WHERE t.name = ? AND c.project_id = ?
                        ORDER BY ct.context_id DESC
                        LIMIT ?
                    """,
                        (tag_name.strip().lower(), project_id, limit),
                    )
                else:
                    # Original query without project filter
                    cursor = await db.execute(
                        """
                        SELECT ct.context_id FROM context_tags ct
                        JOIN tags t ON ct.tag_id = t.id
                        WHERE t.name = ?
                        ORDER BY ct.context_id DESC
                        LIMIT ?
                    """,
                        (tag_name.strip().lower(), limit),
                    )

                rows = await cursor.fetchall()
                return [row[0] for row in rows]

        except Exception as e:
            logger.error(f"Failed to find contexts by tag '{tag_name}': {e}")
            return []

    async def find_contexts_by_multiple_tags(
        self, tags: List[str], limit: int = 50, project_id: Optional[str] = None
    ) -> List[int]:
        """
        Find context IDs that have ANY of the specified tags (OR logic).

        Args:
            tags: List of tag names to search for
            limit: Maximum number of context IDs to return
            project_id: Optional project filter

        Returns:
            List of context IDs that contain any of the specified tags,
            ordered by creation time (newest first)
        """
        if not tags:
            return []

        try:
            # Normalize tag names
            normalized_tags = [tag.strip().lower() for tag in tags if tag.strip()]
            if not normalized_tags:
                return []

            async with self.db_manager.get_connection() as db:
                # Create placeholders for IN clause
                placeholders = ", ".join("?" * len(normalized_tags))

                if project_id is not None:
                    # Filter by tags and project_id using OR logic
                    query = (
                        """
                        SELECT DISTINCT ct.context_id FROM context_tags ct
                        JOIN tags t ON ct.tag_id = t.id
                        JOIN contexts c ON ct.context_id = c.id
                        WHERE t.name IN ("""
                        + placeholders
                        + """) AND c.project_id = ?
                        ORDER BY ct.context_id DESC
                        LIMIT ?
                    """
                    )
                    cursor = await db.execute(
                        query,
                        (*normalized_tags, project_id, limit),
                    )
                else:
                    # Original query without project filter
                    query = (
                        """
                        SELECT DISTINCT ct.context_id FROM context_tags ct
                        JOIN tags t ON ct.tag_id = t.id
                        WHERE t.name IN ("""
                        + placeholders
                        + """)
                        ORDER BY ct.context_id DESC
                        LIMIT ?
                    """
                    )
                    cursor = await db.execute(
                        query,
                        (*normalized_tags, limit),
                    )

                rows = await cursor.fetchall()
                return [row[0] for row in rows]

        except Exception as e:
            logger.error(f"Failed to find contexts by multiple tags {tags}: {e}")
            return []

    async def delete_context_tags(self, context_id: int) -> bool:
        """Delete all tags for a specific context"""
        try:
            async with self.db_manager.get_connection() as db:
                await db.execute(
                    """
                    DELETE FROM context_tags WHERE context_id = ?
                """,
                    (context_id,),
                )
                await db.commit()
                return True

        except Exception as e:
            logger.error(f"Failed to delete tags for context {context_id}: {e}")
            return False

    async def cleanup_unused_tags(self) -> int:
        """Remove tags that are not linked to any contexts"""
        try:
            async with self.db_manager.get_connection() as db:
                cursor = await db.execute(
                    """
                    DELETE FROM tags
                    WHERE id NOT IN (SELECT DISTINCT tag_id FROM context_tags)
                """
                )
                await db.commit()
                return cursor.rowcount

        except Exception as e:
            logger.error(f"Failed to cleanup unused tags: {e}")
            return 0

    async def load_context_tags_batch(self, context_ids: List[int]) -> Dict[int, List[str]]:
        """
        Load tags for multiple contexts in a single query to avoid N+1 problem.

        Args:
            context_ids: List of context IDs to load tags for

        Returns:
            Dictionary mapping context_id -> list of tag names
        """
        try:
            if not context_ids:
                return {}

            async with self.db_manager.get_connection() as db:
                # Create placeholders for IN clause
                placeholders = ",".join("?" * len(context_ids))

                query = (
                    """
                    SELECT ct.context_id, t.name
                    FROM context_tags ct
                    JOIN tags t ON ct.tag_id = t.id
                    WHERE ct.context_id IN ("""
                    + placeholders
                    + """)
                    ORDER BY ct.context_id, t.name
                    """
                )
                cursor = await db.execute(
                    query,
                    context_ids,
                )

                rows = await cursor.fetchall()

                # Group tags by context_id
                context_tags = {}
                for context_id, tag_name in rows:
                    if context_id not in context_tags:
                        context_tags[context_id] = []
                    context_tags[context_id].append(tag_name)

                # Ensure all requested context_ids are in result (even if no tags)
                for context_id in context_ids:
                    if context_id not in context_tags:
                        context_tags[context_id] = []

                return context_tags

        except Exception as e:
            logger.error(f"Failed to load tags batch for contexts {context_ids}: {e}")
            return {}
