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

"""Redis Analytics Service

Handles analytics operations: storage stats, cleanup, high importance contexts, and init contexts.
"""

import json
import logging
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

# Module-level logger
logger = logging.getLogger(__name__)

from .connection_service import RedisConnectionService


class RedisAnalyticsService:
    """Service for managing analytics and statistics in Redis."""

    def __init__(self, connection_service: RedisConnectionService, context_service=None):
        self.connection = connection_service
        self.context_service = context_service

    async def get_storage_stats(self) -> Dict[str, Any]:
        """Get Redis storage statistics."""
        try:
            redis = await self.connection.get_connection()

            # Count contexts
            context_pattern = self.connection.make_key("context", "*")
            context_keys = []
            async for key in redis.scan_iter(match=context_pattern):
                context_keys.append(key)

            # Count projects
            projects_key = self.connection.make_key("projects")
            project_count = await redis.hlen(projects_key)

            # Memory usage (approximate)
            info = await redis.info("memory")
            memory_used = info.get("used_memory", 0)

            ttl_seconds = getattr(self.connection, "ttl_seconds", None)
            return {
                "provider": "redis",
                "total_contexts": len(context_keys),
                "total_projects": project_count,
                "memory_used_bytes": memory_used,
                "ttl_seconds": ttl_seconds,
                "connection_info": f"{self.connection.host}:{self.connection.port}/{self.connection.db}",
            }

        except Exception as e:

            logger.error(f"Error getting Redis storage stats: {e}")
            return {"provider": "redis", "error": str(e)}

    async def cleanup_expired(self) -> int:
        """Clean up expired contexts in Redis.
        Redis handles expiration automatically, so this is mostly a no-op.
        """
        try:
            # For demonstration, we could implement manual cleanup logic here
            # For now, just return 0 since Redis auto-expires
            return 0

        except Exception as e:

            logger.error(f"Error in Redis cleanup: {e}")
            return 0

    async def load_init_contexts(
        self, project_id: Optional[str] = None, limit: int = 10
    ) -> Dict[str, Any]:
        """Load contexts for session initialization with instruction.
        Required by server.py for session startup.
        """
        try:
            # Load contexts using context service if available
            contexts = []
            if self.context_service:
                contexts = await self.context_service.load_contexts(
                    project_id=project_id, limit=limit
                )

            return {
                "contexts": contexts,
                "init_instruction": "Memory system ready - Redis provider active",
            }
        except Exception as e:
            return {
                "contexts": [],
                "init_instruction": f"Memory system error: {str(e)}",
            }

    async def load_high_importance_contexts(self, limit: int = 5) -> List[Dict[str, Any]]:
        """Load high-importance contexts across all projects.
        Required by server.py for startup context resource.
        """
        try:
            redis = await self.connection.get_connection()

            # Get all context keys
            pattern = self.connection.make_key("context:*")
            context_keys = await redis.keys(pattern)

            high_importance_contexts = []

            for key in context_keys[: limit * 3]:  # Get more than needed, filter by importance
                context_json = await redis.get(key)
                if context_json:
                    context = json.loads(context_json)
                    if context.get("importance_level", 0) >= 7:  # High importance threshold
                        high_importance_contexts.append(context)

                if len(high_importance_contexts) >= limit:
                    break

            # Sort by importance and creation time
            high_importance_contexts.sort(
                key=lambda x: (x.get("importance_level", 0), x.get("created_at", "")), reverse=True
            )

            return high_importance_contexts[:limit]

        except Exception as e:

            logger.error(f"Error loading high importance contexts from Redis: {e}")
            return []
