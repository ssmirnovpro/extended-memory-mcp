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

"""Redis Tag Service

Handles tag operations: get context tags, add tags to contexts, and tag management.
"""

import json
import logging
from datetime import datetime, timezone
from typing import Any, Dict, List

# Module-level logger
logger = logging.getLogger(__name__)

from .connection_service import RedisConnectionService


class RedisTagService:
    """Service for managing tag operations in Redis."""

    def __init__(self, connection_service: RedisConnectionService):
        self.connection = connection_service

    async def get_context_tags(self, context_id: str) -> List[str]:
        """Get tags for specific context."""
        try:
            redis = await self.connection.get_connection()

            context_key = self.connection.make_key("context", context_id)
            context_json = await redis.get(context_key)

            if context_json:
                context_data = json.loads(context_json)
                return context_data.get("tags", [])
            return []

        except Exception as e:

            logger.error(f"Error getting context tags from Redis: {e}")
            return []

    async def add_context_tag(self, context_id: str, tag: str) -> bool:
        """Add tag to context in Redis."""
        try:
            redis = await self.connection.get_connection()

            context_key = self.connection.make_key("context", context_id)
            context_json = await redis.get(context_key)

            if not context_json:
                return False

            context_data = json.loads(context_json)
            tags = context_data.get("tags", [])

            if tag not in tags:
                tags.append(tag)
                context_data["tags"] = tags
                context_data["updated_at"] = datetime.now(timezone.utc).isoformat()

                # Update context
                ttl_seconds = getattr(self.connection, "ttl_seconds", None)
                await redis.set(context_key, json.dumps(context_data), ex=ttl_seconds)

                # Add to tag index
                tag_contexts_key = self.connection.make_key("tag", tag, "contexts")
                await redis.lpush(tag_contexts_key, context_id)
                if ttl_seconds:
                    await redis.expire(tag_contexts_key, ttl_seconds)

            return True

        except Exception as e:

            logger.error(f"Error adding tag to context in Redis: {e}")
            return False

    async def get_popular_tags(
        self,
        limit: int = 10,
        min_usage: int = 2,
        recent_hours: int = 24,
        project_id: str = None,
    ) -> List[Dict[str, Any]]:
        """
        Get popular tags with usage count, Redis implementation.

        Note: This is a simplified implementation for Redis.
        Complex SQL-like queries are not efficient in Redis.
        """
        try:
            redis = await self.connection.get_connection()

            # Get all tag patterns
            tag_pattern = self.connection.make_key("tag", "*", "contexts")
            tag_keys = await redis.keys(tag_pattern)

            tag_counts = {}

            for tag_key in tag_keys:
                # Extract tag name from key pattern
                # Handle both bytes and string keys from Redis
                if isinstance(tag_key, bytes):
                    tag_key_str = tag_key.decode("utf-8")
                else:
                    tag_key_str = str(tag_key)

                key_parts = tag_key_str.split(":")
                if len(key_parts) >= 3:
                    tag_name = key_parts[-2]  # tag name is before "contexts"

                    # Get context IDs for this tag
                    context_ids = await redis.lrange(tag_key, 0, -1)

                    # Filter by project if specified
                    if project_id:
                        filtered_ids = []
                        for context_id in context_ids:
                            context_key = self.connection.make_key("context", context_id)
                            context_json = await redis.get(context_key)
                            if context_json:
                                context_data = json.loads(context_json)
                                if context_data.get("project_id") == project_id:
                                    filtered_ids.append(context_id)
                        context_count = len(filtered_ids)
                    else:
                        context_count = len(context_ids)

                    if context_count >= min_usage:
                        tag_counts[tag_name] = context_count

            # Sort by usage count DESC, then tag name ASC for deterministic results
            sorted_tags = sorted(tag_counts.items(), key=lambda x: (-x[1], x[0]))[:limit]

            return [{"tag": tag, "count": count} for tag, count in sorted_tags]

        except Exception as e:
            logger.error(f"Error getting popular tags from Redis: {e}")
            return []

    async def find_contexts_by_multiple_tags(
        self, tags: List[str], limit: int = 50, project_id: str = None
    ) -> List[str]:  # Changed from List[int] to List[str] for Redis UUIDs
        """
        Find context IDs that have any of the specified tags (OR logic).
        Redis implementation using tag indexes.

        Returns:
            List[str]: Context IDs as strings (UUIDs in Redis)
        """
        try:
            redis = await self.connection.get_connection()

            all_context_ids = set()

            for tag in tags:
                tag_contexts_key = self.connection.make_key("tag", tag.lower(), "contexts")
                context_ids = await redis.lrange(tag_contexts_key, 0, -1)
                all_context_ids.update(context_ids)

            # Filter by project if specified (return strings, not ints for Redis UUIDs)
            result_ids = []
            for context_id in all_context_ids:
                if project_id:
                    context_key = self.connection.make_key("context", context_id)
                    context_json = await redis.get(context_key)
                    if context_json:
                        context_data = json.loads(context_json)
                        if context_data.get("project_id") == project_id:
                            # Redis uses UUID strings, not integers
                            result_ids.append(str(context_id))
                else:
                    # Redis uses UUID strings, not integers
                    result_ids.append(str(context_id))

                if len(result_ids) >= limit:
                    break

            return result_ids[:limit]

        except Exception as e:
            logger.error(f"Error finding contexts by multiple tags in Redis: {e}")
            return []

    async def load_context_tags(self, context_id: int) -> List[str]:
        """
        Load tags for a context by integer ID.
        Alias for get_context_tags to maintain compatibility.
        """
        return await self.get_context_tags(str(context_id))

    # ==========================================
    # OPTIMIZED METHODS - N+1 FIXES
    # ==========================================

    async def get_popular_tags_optimized(
        self,
        limit: int = 10,
        min_usage: int = 2,
        recent_hours: int = 24,
        project_id: str = None,
    ) -> List[Dict[str, Any]]:
        """
        OPTIMIZED: Get popular tags with usage count - fixes N+1 performance issues.

        Performance improvements:
        - Uses Redis pipeline for batch LRANGE operations
        - Uses MGET for batch context lookups during project filtering
        - Reduces Redis operations from 1 + N_tags + N_contexts to ~3 operations

        Expected speedup: 8-10x improvement (similar to SQLite optimizations)
        """
        try:
            redis = await self.connection.get_connection()

            # Step 1: Get all tag patterns (single KEYS operation)
            tag_pattern = self.connection.make_key("tag", "*", "contexts")
            tag_keys = await redis.keys(tag_pattern)

            if not tag_keys:
                return []

            # Step 2: Batch get all tag context lists using pipeline
            pipe = redis.pipeline()
            tag_names = []

            for tag_key in tag_keys:
                # Extract tag name from key pattern
                # Handle both bytes and string keys from Redis
                if isinstance(tag_key, bytes):
                    tag_key_str = tag_key.decode("utf-8")
                else:
                    tag_key_str = str(tag_key)

                key_parts = tag_key_str.split(":")
                if len(key_parts) >= 3:
                    tag_name = key_parts[-2]  # tag name is before "contexts"
                    tag_names.append(tag_name)
                    pipe.lrange(tag_key, 0, -1)  # Add to pipeline

            # Execute pipeline to get all tag context lists at once
            tag_context_lists = await pipe.execute()

            # Step 3: Project filtering with batch MGET (if needed)
            tag_counts = {}

            if project_id:
                # Collect all unique context IDs for batch lookup
                all_context_ids = set()
                tag_to_contexts = {}

                for i, context_ids in enumerate(tag_context_lists):
                    if i < len(tag_names):
                        tag_name = tag_names[i]
                        tag_to_contexts[tag_name] = [str(cid) for cid in context_ids]
                        all_context_ids.update(tag_to_contexts[tag_name])

                # Batch get all context data (single MGET operation)
                if all_context_ids:
                    context_keys = [
                        self.connection.make_key("context", cid) for cid in all_context_ids
                    ]
                    context_data_list = await redis.mget(context_keys)

                    # Build context_id -> project_id mapping
                    context_projects = {}
                    context_ids_list = list(all_context_ids)

                    for i, context_data in enumerate(context_data_list):
                        if context_data and i < len(context_ids_list):
                            try:
                                data = json.loads(context_data)
                                context_id = context_ids_list[i]
                                context_projects[context_id] = data.get("project_id")
                            except (json.JSONDecodeError, IndexError):
                                continue

                    # Count contexts per tag that match project
                    for tag_name, context_ids in tag_to_contexts.items():
                        filtered_count = sum(
                            1 for cid in context_ids if context_projects.get(cid) == project_id
                        )
                        if filtered_count >= min_usage:
                            tag_counts[tag_name] = filtered_count
            else:
                # No project filtering - just count context lists
                for i, context_ids in enumerate(tag_context_lists):
                    if i < len(tag_names):
                        tag_name = tag_names[i]
                        context_count = len(context_ids)
                        if context_count >= min_usage:
                            tag_counts[tag_name] = context_count

            # Sort by usage count DESC, then tag name ASC for deterministic results
            sorted_tags = sorted(tag_counts.items(), key=lambda x: (-x[1], x[0]))[:limit]

            return [{"tag": tag, "count": count} for tag, count in sorted_tags]

        except Exception as e:
            logger.error(f"Error getting popular tags from Redis (optimized): {e}")
            return []

    async def find_contexts_by_multiple_tags_optimized(
        self, tags: List[str], limit: int = 50, project_id: str = None
    ) -> List[str]:  # Changed from List[int] to List[str] for Redis UUIDs
        """
        OPTIMIZED: Find context IDs that have any of the specified tags (OR logic).
        Fixes N+1 performance issues.

        Performance improvements:
        - Uses pipeline for batch LRANGE operations
        - Uses MGET for batch context lookups when project filtering
        - Reduces Redis calls from N_tags + N_contexts to 2-3 operations

        Expected speedup: 8-10x improvement
        """
        try:
            redis = await self.connection.get_connection()

            if not tags:
                return []

            # Step 1: Batch get all tag context lists using pipeline
            pipe = redis.pipeline()
            tag_keys = []

            for tag in tags:
                if tag and tag.strip():
                    tag_contexts_key = self.connection.make_key(
                        "tag", tag.lower().strip(), "contexts"
                    )
                    tag_keys.append(tag_contexts_key)
                    pipe.lrange(tag_contexts_key, 0, -1)

            if not tag_keys:
                return []

            # Execute pipeline to get all tag context lists at once
            tag_context_lists = await pipe.execute()

            # Combine all context IDs (OR logic)
            all_context_ids = set()
            for context_list in tag_context_lists:
                if context_list:
                    # Convert bytes to strings and add to set
                    for ctx_id in context_list:
                        ctx_id_str = ctx_id.decode() if isinstance(ctx_id, bytes) else str(ctx_id)
                        all_context_ids.add(ctx_id_str)

            if not all_context_ids:
                return []

            # Step 2: Project filtering with batch MGET (if needed)
            if project_id:
                # Batch get all context data for project filtering
                context_keys = [
                    self.connection.make_key("context", ctx_id) for ctx_id in all_context_ids
                ]
                context_data_list = await redis.mget(context_keys)

                # Filter contexts by project_id
                filtered_ids = []
                context_ids_list = list(all_context_ids)

                for i, context_data in enumerate(context_data_list):
                    if context_data and i < len(context_ids_list):
                        try:
                            data = json.loads(context_data)
                            if data.get("project_id") == project_id:
                                # Redis uses UUID strings, not integers
                                filtered_ids.append(str(context_ids_list[i]))
                        except json.JSONDecodeError:
                            continue

                    # Early exit if we have enough results
                    if len(filtered_ids) >= limit:
                        break

                return filtered_ids[:limit]
            else:
                # No project filtering - return UUIDs as strings
                result_ids = []
                for context_id in all_context_ids:
                    # Redis uses UUID strings, not integers
                    result_ids.append(str(context_id))

                    if len(result_ids) >= limit:
                        break

                return result_ids[:limit]

        except Exception as e:
            logger.error(f"Error finding contexts by multiple tags in Redis (optimized): {e}")
            return []

    # ==========================================
    # FEATURE FLAG INTEGRATION
    # ==========================================

    def _use_optimized_methods(self) -> bool:
        """
        Feature flag to enable optimized Redis methods.

        Can be controlled via environment variable REDIS_USE_OPTIMIZED=true
        Default: False (use original methods for backward compatibility)
        """
        import os

        return os.getenv("REDIS_USE_OPTIMIZED", "false").lower() in ("true", "1", "yes")

    async def get_popular_tags_with_optimization(
        self,
        limit: int = 10,
        min_usage: int = 2,
        recent_hours: int = 24,
        project_id: str = None,
    ) -> List[Dict[str, Any]]:
        """
        Wrapper method that chooses between original and optimized implementation.

        Use this method in production code for safe rollout of optimizations.
        """
        if self._use_optimized_methods():
            return await self.get_popular_tags_optimized(
                limit=limit, min_usage=min_usage, recent_hours=recent_hours, project_id=project_id
            )
        else:
            return await self.get_popular_tags(
                limit=limit, min_usage=min_usage, recent_hours=recent_hours, project_id=project_id
            )

    async def find_contexts_by_multiple_tags_with_optimization(
        self, tags: List[str], limit: int = 50, project_id: str = None
    ) -> List[str]:  # Changed from List[int] to List[str] for Redis UUIDs
        """
        Wrapper method that chooses between original and optimized implementation.

        Use this method in production code for safe rollout of optimizations.
        """
        if self._use_optimized_methods():
            return await self.find_contexts_by_multiple_tags_optimized(
                tags=tags, limit=limit, project_id=project_id
            )
        else:
            return await self.find_contexts_by_multiple_tags(
                tags=tags, limit=limit, project_id=project_id
            )
