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
Context Service - Domain service for context management operations.

Handles all business logic related to context storage, retrieval, and manipulation.
Follows Single Responsibility Principle by focusing only on context operations.
"""

import logging
from typing import Any, Dict, List, Optional

from ..context_repository import ContextRepository
from ..database_manager import DatabaseManager
from ..tags_repository import TagsRepository

logger = logging.getLogger(__name__)


class ContextService:
    """
    Domain service for context management operations.

    Responsible for:
    - Context creation and storage
    - Context retrieval with filtering
    - Context updates and deletions
    - Tag management for contexts
    """

    def __init__(self, db_manager: DatabaseManager):
        """
        Initialize context service with required dependencies.

        Args:
            db_manager: Database manager for transaction handling
        """
        self.db_manager = db_manager
        self.context_repo = ContextRepository(db_manager)
        self.tags_repo = TagsRepository(db_manager)

    async def save_context(
        self,
        content: str,
        importance_level: int,
        project_id: Optional[str] = None,
        tags: Optional[List[str]] = None,
    ) -> Optional[int]:
        """
        Save context to database with normalized tags.

        Args:
            content: The context content
            importance_level: 1-10, importance rating
            project_id: Project isolation (None for global)
            tags: Tags for searchability

        Returns:
            Context ID if successful, None if failed
        """
        try:
            # Ensure database is initialized
            await self.db_manager.ensure_database()

            # Save the context
            context_id = await self.context_repo.save_context(
                content=content,
                importance_level=importance_level,
                project_id=project_id,
                tags=tags,
            )

            # Save tags if provided and context was saved successfully
            if context_id and tags:
                await self.tags_repo.save_context_tags(context_id, tags)

            logger.info(
                f"Saved context {context_id} for project {project_id} with {len(tags) if tags else 0} tags"
            )
            return context_id

        except Exception as e:
            logger.error(f"Failed to save context: {e}")
            return None

    async def load_contexts(
        self,
        project_id: Optional[str] = None,
        importance_min: int = 1,
        limit: int = 50,
        offset: int = 0,
        search_query: Optional[str] = None,
        tags_filter: Optional[List[str]] = None,
    ) -> List[Dict[str, Any]]:
        """
        Load contexts with filtering.

        Args:
            project_id: Filter by project (None for all projects)
            importance_min: Minimum importance level
            limit: Maximum number of contexts to return
            offset: Skip this many contexts (pagination)
            search_query: Search in content and metadata
            tags_filter: Filter by tags (list of tag names)

        Returns:
            List of context dictionaries with tags included
        """
        try:
            await self.db_manager.ensure_database()

            # Handle tags_filter by finding contexts with those tags first
            if tags_filter:
                # Find contexts that have any of the specified tags, filtered by project
                matching_context_ids = set()
                for tag in tags_filter:
                    tag_context_ids = await self.tags_repo.find_contexts_by_tag(
                        tag, limit=1000, project_id=project_id
                    )
                    matching_context_ids.update(tag_context_ids)

                # If no matching contexts found, return empty
                if not matching_context_ids:
                    return []

                # Use optimized SQL WHERE IN instead of Python filtering
                contexts = await self.context_repo.load_contexts_by_ids(
                    [int(context_id) for context_id in matching_context_ids]
                )

                # Apply additional filters that were not possible in the ID query
                filtered_contexts = []
                for context in contexts:
                    # project_id filter already applied in find_contexts_by_tag, but keep for safety
                    if project_id is not None and context.get("project_id") != project_id:
                        continue
                    # Check context_type filter
                    # Check importance filter (context_type filtering removed)
                    if context.get("importance_level", 0) < importance_min:
                        continue
                    filtered_contexts.append(context)

                # Apply limit
                contexts = filtered_contexts[:limit]
            else:
                # Normal loading without tag filter
                contexts = await self.context_repo.load_contexts(
                    project_id=project_id,
                    context_type=context_type,
                    importance_min=importance_min,
                    limit=limit,
                    offset=offset,
                )

            # Handle search_query by filtering content (simple implementation)
            if search_query and contexts:
                search_lower = search_query.lower()
                contexts = [c for c in contexts if search_lower in c.get("content", "").lower()]

            # Load tags for each context
            for context in contexts:
                context["tags"] = await self.tags_repo.load_context_tags(context["id"])

            return contexts

        except Exception as e:
            logger.error(f"Failed to load contexts: {e}")
            return []

    async def delete_context(self, context_id: int) -> bool:
        """Delete context by ID."""
        return await self.context_repo.delete_context(context_id)

    async def get_context_by_id(self, context_id: int) -> Optional[Dict[str, Any]]:
        """Get single context by ID with tags."""
        context = await self.context_repo.get_context_by_id(context_id)
        if context:
            context["tags"] = await self.tags_repo.load_context_tags(context_id)
        return context

    async def count_contexts(self, project_id: Optional[str] = None) -> int:
        """Count total contexts, optionally filtered by project."""
        return await self.context_repo.count_contexts(project_id)

    async def get_contexts_by_importance(
        self, min_importance: int = 7, limit: int = 30
    ) -> List[Dict[str, Any]]:
        """Load high-importance contexts across all projects."""
        contexts = await self.context_repo.get_contexts_by_importance(min_importance, limit)

        # Add tags to each context
        for context in contexts:
            context["tags"] = await self.tags_repo.load_context_tags(context["id"])

        return contexts
