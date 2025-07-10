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

"""Redis Context Service

Handles context operations: save, load, delete, search, and forget contexts.
"""

import json
import logging
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

# Module-level logger
logger = logging.getLogger(__name__)

from .connection_service import RedisConnectionService


class RedisContextService:
    """Service for managing context operations in Redis."""

    def __init__(self, connection_service: RedisConnectionService):
        self.connection = connection_service

    async def save_context(
        self,
        content: str,
        importance_level: int,
        project_id: Optional[str] = None,
        tags: Optional[List[str]] = None,
    ) -> Optional[str]:
        """Save context to Redis.

        Storage structure:
        - context:{context_id} = {full context data}
        - project:{project_id}:contexts = [list of context_ids]
        - tag:{tag}:contexts = [list of context_ids]
        """
        try:
            redis = await self.connection.get_connection()

            # Generate unique context ID
            context_id = str(uuid.uuid4())

            # Prepare context data
            context_data = {
                "id": context_id,
                "content": content,
                "importance_level": importance_level,
                "project_id": project_id,
                "tags": tags or [],
                "created_at": datetime.now(timezone.utc).isoformat(),
                "updated_at": datetime.now(timezone.utc).isoformat(),
            }

            # Store main context
            context_key = self.connection.make_key("context", context_id)
            ttl_seconds = getattr(self.connection, "ttl_seconds", None)
            await redis.set(context_key, json.dumps(context_data), ex=ttl_seconds)

            # Add to project index
            if project_id:
                project_contexts_key = self.connection.make_key("project", project_id, "contexts")
                await redis.lpush(project_contexts_key, context_id)
                if ttl_seconds:
                    await redis.expire(project_contexts_key, ttl_seconds)

                # Update project last accessed (will implement in project_service)
                # await self._update_project_accessed(project_id)

            # Add to tag indices
            if tags:
                for tag in tags:
                    tag_contexts_key = self.connection.make_key("tag", tag, "contexts")
                    await redis.lpush(tag_contexts_key, context_id)
                    if ttl_seconds:
                        await redis.expire(tag_contexts_key, ttl_seconds)

            return context_id

        except Exception as e:

            logger.error(f"Error saving context to Redis: {e}")
            return None

    async def load_contexts(
        self,
        project_id: Optional[str] = None,
        limit: int = 50,
        importance_threshold: int = 1,
        tags_filter: Optional[List[str]] = None,
    ) -> List[Dict[str, Any]]:
        """Load contexts from Redis with filtering."""
        try:
            redis = await self.connection.get_connection()
            contexts = []

            # Handle tags_filter first if provided (use SQLite-compatible approach)
            if tags_filter:
                # Use tag service if available (injected by redis_provider)
                if hasattr(self, "tag_service") and self.tag_service:
                    # SQLite-compatible approach: use find_contexts_by_multiple_tags
                    context_ids = await self.tag_service.find_contexts_by_multiple_tags(
                        tags=tags_filter, limit=limit, project_id=project_id
                    )

                    if not context_ids:
                        return []

                    # Convert to strings for consistent handling
                    context_id_strings = [str(cid) for cid in context_ids]
                    return await self.load_contexts_by_ids(context_id_strings)
                else:
                    # Fallback: direct Redis implementation (legacy)
                    matching_context_ids = set()

                    for tag in tags_filter:
                        if not tag or not tag.strip():
                            continue

                        tag_normalized = tag.strip().lower()
                        tag_contexts_key = self.connection.make_key(
                            "tag", tag_normalized, "contexts"
                        )
                        tag_context_ids = await redis.smembers(tag_contexts_key)

                        # Convert bytes to strings and add to matching set
                        for ctx_id in tag_context_ids:
                            matching_context_ids.add(
                                ctx_id.decode() if isinstance(ctx_id, bytes) else str(ctx_id)
                            )

                    # If no contexts found with specified tags, return empty list
                    if not matching_context_ids:
                        return []

                    # Filter by project if specified
                    if project_id:
                        project_contexts_key = self.connection.make_key(
                            "project", project_id, "contexts"
                        )
                        project_context_ids = await redis.lrange(project_contexts_key, 0, -1)
                        project_context_set = {
                            (ctx_id.decode() if isinstance(ctx_id, bytes) else str(ctx_id))
                            for ctx_id in project_context_ids
                        }
                        # Intersection: contexts that have the tags AND are in the project
                        matching_context_ids = matching_context_ids.intersection(
                            project_context_set
                        )

                    context_ids = list(matching_context_ids)[:limit]

            elif project_id:
                # Load from project index
                project_contexts_key = self.connection.make_key("project", project_id, "contexts")
                context_ids = await redis.lrange(project_contexts_key, 0, limit - 1)
                context_ids = [
                    (ctx_id.decode() if isinstance(ctx_id, bytes) else str(ctx_id))
                    for ctx_id in context_ids
                ]
            else:
                # Load all contexts (scan for context:* keys)
                context_keys = []
                pattern = self.connection.make_key("context", "*")
                async for key in redis.scan_iter(match=pattern):
                    context_keys.append(key)

                # Extract ALL context IDs first (don't limit here!)
                context_ids = []
                for key in context_keys:
                    # Handle both bytes and string keys from Redis
                    if isinstance(key, bytes):
                        key_str = key.decode("utf-8")
                    else:
                        key_str = str(key)
                    context_ids.append(key_str.split(":")[-1])

            # Load context data
            for context_id in context_ids:
                context_key = self.connection.make_key("context", context_id)
                context_json = await redis.get(context_key)

                if context_json:
                    context_data = json.loads(context_json)

                    # Apply filters
                    if context_data.get("importance_level", 0) < importance_threshold:
                        continue

                    contexts.append(context_data)

            # Sort by created_at DESC, then by id for deterministic order
            contexts.sort(key=lambda x: (x.get("created_at", ""), x.get("id", "")), reverse=True)
            return contexts[:limit]

        except Exception as e:
            logger.error(f"Error loading contexts from Redis: {e}")
            return []

    async def load_context(self, context_id: str) -> Optional[Dict[str, Any]]:
        """Load single context by ID from Redis."""
        try:
            redis = await self.connection.get_connection()

            context_key = self.connection.make_key("context", context_id)
            context_json = await redis.get(context_key)

            if context_json:
                return json.loads(context_json)
            return None

        except Exception as e:

            logger.error(f"Error loading context {context_id} from Redis: {e}")
            return None

    async def delete_context(self, context_id: str) -> bool:
        """Delete context and remove from all indices."""
        try:
            redis = await self.connection.get_connection()

            # Get context data first (to clean up indices)
            context_key = self.connection.make_key("context", context_id)
            context_json = await redis.get(context_key)

            if not context_json:
                return False

            context_data = json.loads(context_json)

            # Delete main context
            await redis.delete(context_key)

            # Remove from project index
            project_id = context_data.get("project_id")
            if project_id:
                project_contexts_key = self.connection.make_key("project", project_id, "contexts")
                await redis.lrem(project_contexts_key, 1, context_id)

            # Remove from tag indices
            tags = context_data.get("tags", [])
            for tag in tags:
                tag_contexts_key = self.connection.make_key("tag", tag, "contexts")
                await redis.lrem(tag_contexts_key, 1, context_id)

            return True

        except Exception as e:

            logger.error(f"Error deleting context from Redis: {e}")
            return False

    async def update_context(
        self, context_id: str, content: Optional[str] = None, importance_level: Optional[int] = None
    ) -> bool:
        """Update existing context in Redis."""
        try:
            redis = await self.connection.get_connection()

            context_key = self.connection.make_key("context", context_id)
            context_json = await redis.get(context_key)

            if not context_json:
                return False

            context_data = json.loads(context_json)

            # Update fields
            if content is not None:
                context_data["content"] = content
            if importance_level is not None:
                context_data["importance_level"] = importance_level

            context_data["updated_at"] = datetime.now(timezone.utc).isoformat()

            # Save updated context
            ttl_seconds = getattr(self.connection, "ttl_seconds", None)
            await redis.set(context_key, json.dumps(context_data), ex=ttl_seconds)
            return True

        except Exception as e:

            logger.error(f"Error updating context in Redis: {e}")
            return False

    async def search_contexts(self, filters: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Search contexts with complex filters in Redis."""
        try:
            redis = await self.connection.get_connection()

            # Extract filters
            project_id = filters.get("project_id")
            min_importance = filters.get("min_importance", 1)
            tags_filter = filters.get("tags", [])
            content_search = filters.get(
                "content_search"
            )  # RESERVED: for future advanced search features
            limit = filters.get("limit", 100)

            # Start with all contexts or project-specific contexts
            if project_id:
                pattern = self.connection.make_key("context", f"{project_id}:*")
            else:
                pattern = self.connection.make_key("context", "*")

            context_keys = await redis.keys(pattern)
            contexts = []

            for key in context_keys:
                context_json = await redis.get(key)
                if context_json:
                    context_data = json.loads(context_json)

                    # Apply filters
                    if context_data.get("importance_level", 0) < min_importance:
                        continue
                    # Apply content search filter (RESERVED: for future advanced search features)
                    if (
                        content_search
                        and content_search.lower() not in context_data.get("content", "").lower()
                    ):
                        continue

                    # Check tags filter
                    if tags_filter:
                        context_tags = context_data.get("tags", [])
                        if not any(tag in context_tags for tag in tags_filter):
                            continue

                    contexts.append(context_data)

                    if len(contexts) >= limit:
                        break

            # Sort by importance and creation time (deterministic)
            contexts.sort(
                key=lambda x: (
                    x.get("importance_level", 0),
                    x.get("created_at", ""),
                    x.get("id", ""),
                ),
                reverse=True,
            )
            return contexts[:limit]

        except Exception as e:

            logger.error(f"Error searching contexts in Redis: {e}")
            return []

    async def forget_context(self, context_id: str) -> bool:
        """Alias for delete_context to match server.py expectations."""
        return await self.delete_context(context_id)

    async def load_contexts_by_ids(self, context_ids: List[str]) -> List[Dict[str, Any]]:
        """
        Load specific contexts by their IDs using optimized Redis MGET operation.
        This replaces inefficient Python filtering with direct Redis lookup.

        Args:
            context_ids: List of context identifiers to load

        Returns:
            List of context dictionaries (only found contexts)
        """
        try:
            if not context_ids:
                return []

            redis = await self.connection.get_connection()

            # Create Redis keys for MGET operation
            context_keys = [
                self.connection.make_key("context", context_id) for context_id in context_ids
            ]

            # Use MGET for efficient bulk retrieval
            results = await redis.mget(context_keys)

            contexts = []
            for i, result in enumerate(results):
                if result:  # Skip None results (missing contexts)
                    try:
                        # Handle both bytes and string results from Redis
                        if isinstance(result, bytes):
                            context_data = json.loads(result.decode("utf-8"))
                        else:
                            context_data = json.loads(result)
                        contexts.append(context_data)
                    except (json.JSONDecodeError, UnicodeDecodeError) as e:
                        logger.warning(f"Failed to decode context {context_ids[i]}: {e}")
                        continue

            # Sort by importance and creation time (deterministic)
            contexts.sort(
                key=lambda x: (
                    x.get("importance_level", 0),
                    x.get("created_at", ""),
                    x.get("id", ""),
                ),
                reverse=True,
            )

            return contexts

        except Exception as e:
            logger.error(f"Error loading contexts by IDs from Redis: {e}")
            return []
