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
Redis Storage Provider - Service-based implementation for Extended Memory MCP.

Refactored to use service layer architecture, following the same pattern as SQLite provider.
All business logic is extracted into dedicated services for better maintainability.
"""

import json
import logging
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

try:
    import redis.asyncio as redis

    # Verify redis-py async support
    if not hasattr(redis, "Redis"):
        raise ImportError(
            "redis-py async support not found. Extended Memory MCP requires redis[hiredis]>=4.5.0.\\n"
            "Please install: pip install 'redis[hiredis]>=4.5.0'"
        )

    REDIS_AVAILABLE = True
    REDIS_VERSION_ERROR = None

except ImportError as e:
    redis = None
    REDIS_AVAILABLE = False
    REDIS_VERSION_ERROR = str(e)

from ...interfaces.storage_provider import IStorageProvider
from .services import (
    RedisAnalyticsService,
    RedisConnectionService,
    RedisContextService,
    RedisTagService,
)


class RedisStorageProvider(IStorageProvider):
    """Redis-based storage provider using service layer architecture."""

    def __init__(
        self,
        host: str = "localhost",
        port: int = 6379,
        db: int = 0,
        password: Optional[str] = None,
        key_prefix: Optional[str] = None,
        ttl_hours: Optional[int] = None,
    ):
        """Initialize Redis storage provider with service architecture."""
        if not REDIS_AVAILABLE:
            raise ImportError(
                f"Redis storage provider unavailable: {REDIS_VERSION_ERROR}\\n"
                "Install redis with: pip install 'redis[hiredis]>=4.5.0'"
            )

        # Get defaults from config if not provided
        from ....config import get_env_default

        if key_prefix is None:
            key_prefix = get_env_default("REDIS_KEY_PREFIX", "extended_memory")
        if ttl_hours is None:
            ttl_hours = get_env_default("REDIS_TTL_HOURS", 8760)

        # Store constructor parameters
        self.host = host
        self.port = port
        self.db = db
        self.password = password
        self.key_prefix = key_prefix
        self.ttl_hours = ttl_hours
        self.ttl_seconds = ttl_hours * 3600 if ttl_hours > 0 else None

        # Initialize logger
        self.logger = logging.getLogger(__name__)

        # Initialize connection service
        self.connection_service = RedisConnectionService(
            host=host, port=port, db=db, password=password, key_prefix=key_prefix
        )

        # Store ttl_seconds for services to access
        self.connection_service.ttl_seconds = ttl_hours * 3600 if ttl_hours > 0 else None

        # Initialize all services
        self.context_service = RedisContextService(self.connection_service)
        self.tag_service = RedisTagService(self.connection_service)
        self.analytics_service = RedisAnalyticsService(
            self.connection_service, self.context_service
        )

        # Inject tag_service into context_service for tags_filter integration
        self.context_service.tag_service = self.tag_service

        # Create alias for compatibility with SQLite provider
        self.tags_repo = self.tag_service

    # Connection Management
    async def initialize(self) -> bool:
        """Initialize Redis storage."""
        return await self.connection_service.initialize()

    async def health_check(self) -> bool:
        """Check Redis connection health."""
        return await self.connection_service.health_check()

    async def close(self) -> None:
        """Close Redis connection."""
        await self.connection_service.close()

    # Context Operations
    async def save_context(
        self,
        content: str,
        importance_level: int,
        project_id: Optional[str] = None,
        tags: Optional[List[str]] = None,
    ) -> Optional[str]:
        """Save context using context service."""
        return await self.context_service.save_context(content, importance_level, project_id, tags)

    async def load_contexts(
        self,
        project_id: Optional[str] = None,
        limit: int = 50,
        importance_threshold: int = 1,
        tags_filter: Optional[List[str]] = None,
    ) -> ContextList:
        """Load contexts using context service."""
        return await self.context_service.load_contexts(
            project_id, limit, importance_threshold, tags_filter
        )

    async def load_context(self, context_id: str) -> Optional[ContextData]:
        """Load single context using context service."""
        return await self.context_service.load_context(context_id)

    async def load_contexts_by_ids(self, context_ids: List[str]) -> ContextList:
        """
        Load specific contexts by their IDs using optimized Redis MGET operation.
        """
        return await self.context_service.load_contexts_by_ids(context_ids)

    async def delete_context(self, context_id: str) -> bool:
        """Delete context using context service."""
        return await self.context_service.delete_context(context_id)

    async def update_context(
        self, context_id: str, content: Optional[str] = None, importance_level: Optional[int] = None
    ) -> bool:
        """Update context using context service."""
        return await self.context_service.update_context(context_id, content, importance_level)

    async def forget_context(self, context_id: str) -> bool:
        """Forget context using context service."""
        return await self.context_service.forget_context(context_id)

    async def search_contexts(self, filters: SearchFilters) -> ContextList:
        """Search contexts using context service."""
        return await self.context_service.search_contexts(filters)

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
        return await self.tag_service.find_contexts_by_multiple_tags(
            tags=tags, project_id=project_id, limit=limit
        )

    async def get_popular_tags(
        self, limit: int = 10, min_usage: int = 2, project_id: Optional[str] = None
    ) -> TagList:
        """Get popular tags using tag service."""
        return await self.tag_service.get_popular_tags(
            limit=limit, min_usage=min_usage, project_id=project_id
        )

    async def list_all_projects_global(self) -> ProjectList:
        """List ALL projects globally from context data."""
        try:
            # Simple approach for Redis: get all context keys and extract project_ids
            # Redis-friendly - no complex queries
            redis = await self.connection_service.get_connection()
            pattern = f"{self.key_prefix}:context:*"
            keys = await redis.keys(pattern)

            project_counts = {}
            for key in keys:
                context_json = await redis.get(key)
                if context_json:
                    context_data = json.loads(context_json)
                    project_id = context_data.get("project_id")
                    if project_id:
                        project_counts[project_id] = project_counts.get(project_id, 0) + 1

            projects = []
            for project_id, count in project_counts.items():
                projects.append({"id": project_id, "name": project_id, "context_count": count})

            return projects
        except Exception as e:
            self.logger.error(f"Error listing all projects globally from Redis: {e}")
            return []

    async def update_project_access(self, project_id: str) -> None:
        """Update project access using project service."""

    # Tag Operations
    async def get_context_tags(self, context_id: str) -> List[str]:
        """Get context tags using tag service."""
        return await self.tag_service.get_context_tags(context_id)

    async def add_context_tag(self, context_id: str, tag: str) -> bool:
        """Add context tag using tag service."""
        return await self.tag_service.add_context_tag(context_id, tag)

    # Analytics Operations
    async def get_storage_stats(self) -> StorageStats:
        """Get storage stats using analytics service."""
        return await self.analytics_service.get_storage_stats()

    async def cleanup_expired(self) -> int:
        """Cleanup expired contexts using analytics service."""
        return await self.analytics_service.cleanup_expired()

    async def load_high_importance_contexts(self, limit: int = 5) -> List[Dict[str, Any]]:
        """Load high importance contexts using analytics service."""
        return await self.analytics_service.load_high_importance_contexts(limit)

    async def load_init_contexts(
        self, project_id: Optional[str] = None, limit: int = 10
    ) -> InitContextsResult:
        """Load init contexts using analytics service."""
        return await self.analytics_service.load_init_contexts(project_id, limit)
