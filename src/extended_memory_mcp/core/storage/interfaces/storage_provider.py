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
Storage Provider Interface - Abstract base for all storage implementations.

Defines the contract that all storage providers must implement.
Supports multiple storage backends: SQLite, Redis, PostgreSQL, MongoDB.
"""

from abc import ABC, abstractmethod
from datetime import datetime
from typing import Any, Dict, List, Optional

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


class IStorageProvider(ABC):
    """
    Abstract storage provider interface.

    All storage implementations must implement these methods.
    This ensures we can switch between SQLite, Redis, PostgreSQL, etc.
    without changing business logic.
    """

    @abstractmethod
    async def initialize(self) -> bool:
        """
        Initialize storage provider (create tables, indices, etc.)

        Returns:
            True if initialization successful, False otherwise
        """
        pass

    @abstractmethod
    async def health_check(self) -> bool:
        """
        Check if storage provider is healthy and accessible.

        Returns:
            True if healthy, False if connection issues
        """
        pass

    # Context operations
    @abstractmethod
    async def save_context(
        self,
        content: str,
        importance_level: int,
        project_id: Optional[str] = None,
        tags: Optional[List[str]] = None,
    ) -> Optional[str]:
        """
        Save context to storage.

        Args:
            content: Context content text
            importance_level: 1-10 importance rating
            project_id: Project isolation (None for global)
            tags: Optional tags list

        Returns:
            Context ID if successful, None if failed
        """
        pass

    @abstractmethod
    async def load_context(self, context_id: str) -> Optional[ContextData]:
        """
        Load single context by ID.

        Args:
            context_id: Context identifier

        Returns:
            ContextData if found, None if not found
        """
        pass

    @abstractmethod
    async def load_contexts(
        self,
        project_id: Optional[str] = None,
        limit: int = 50,
        importance_threshold: int = 7,
        tags_filter: Optional[List[str]] = None,
    ) -> ContextList:
        """
        Load contexts from storage with filtering.

        Args:
            project_id: Filter by project (None for all projects)
            limit: Maximum number of contexts to return
            importance_threshold: Minimum importance level (default: 7)
            tags_filter: Filter by tags using OR logic (any of these tags)

        Returns:
            List of ContextData sorted chronologically
        """
        pass

    @abstractmethod
    async def load_contexts_by_ids(self, context_ids: List[str]) -> ContextList:
        """
        Load specific contexts by their IDs (optimized for bulk loading).

        Args:
            context_ids: List of context identifiers to load

        Returns:
            List of ContextData (only found contexts)
        """
        pass

    @abstractmethod
    async def delete_context(self, context_id: str) -> bool:
        """
        Delete context by ID.

        Args:
            context_id: Context identifier

        Returns:
            True if deleted, False if not found or error
        """
        pass

    @abstractmethod
    async def update_context(
        self, context_id: str, content: Optional[str] = None, importance_level: Optional[int] = None
    ) -> bool:
        """
        Update existing context.

        Args:
            context_id: Context identifier
            content: New content (None to keep existing)
            importance_level: New importance (None to keep existing)

        Returns:
            True if updated, False if not found or error
        """
        pass

    @abstractmethod
    async def search_contexts(self, filters: SearchFilters) -> ContextList:
        """
        Search contexts with complex filters.

        Args:
            filters: SearchFilters with filter criteria such as:
                - project_id: Filter by project
                - min_importance: Minimum importance level
                - tags_filter: List of required tags
                - content_search: Text search in content (RESERVED: for future advanced search features)

        Returns:
            List of matching ContextData
        """
        pass

    # Tag operations
    @abstractmethod
    async def get_context_tags(self, context_id: str) -> List[str]:
        """
        Get tags for specific context.

        Args:
            context_id: Context identifier

        Returns:
            List of tag names
        """
        pass

    @abstractmethod
    async def add_context_tag(self, context_id: str, tag: str) -> bool:
        """
        Add tag to context.

        Args:
            context_id: Context identifier
            tag: Tag name to add

        Returns:
            True if added, False if error
        """
        pass

    # Advanced tag operations for Redis/SQLite provider parity
    @abstractmethod
    async def get_popular_tags(
        self, limit: int = 10, min_usage: int = 2, project_id: Optional[str] = None
    ) -> TagList:
        """
        Get popular tags with usage statistics.

        Args:
            limit: Maximum number of tags to return
            min_usage: Minimum usage count for inclusion
            project_id: Filter by project (None for all projects)

        Returns:
            List of PopularTag with usage counts
        """
        pass

    @abstractmethod
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
        pass

    # Analytics and cleanup
    @abstractmethod
    async def get_storage_stats(self) -> StorageStats:
        """
        Get storage statistics.

        Returns:
            StorageStats with storage metrics (size, count, etc.)
        """
        pass

    @abstractmethod
    async def cleanup_expired(self) -> int:
        """
        Clean up expired or old contexts based on retention policy.

        Returns:
            Number of contexts cleaned up
        """
        pass

    @abstractmethod
    async def load_init_contexts(
        self, project_id: Optional[str] = None, limit: int = 30
    ) -> InitContextsResult:
        """
        Load contexts for session initialization with instruction and personality.

        Args:
            project_id: Filter by project (None for all projects)
            limit: Maximum number of contexts to return

        Returns:
            InitContextsResult with init_instruction and contexts
        """
        pass

    @abstractmethod
    async def close(self) -> None:
        """
        Close storage provider connections and cleanup resources.
        """
        pass
