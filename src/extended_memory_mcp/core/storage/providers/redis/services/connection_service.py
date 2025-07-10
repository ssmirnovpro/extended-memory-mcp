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

"""Redis Connection Service

Handles Redis connection management, initialization, and health checks.
"""

import logging
from typing import Optional

import redis.asyncio as redis

# Module-level logger
logger = logging.getLogger(__name__)


class RedisConnectionService:
    """Service for managing Redis connections and basic operations."""

    def __init__(
        self,
        host: str = "localhost",
        port: int = 6379,
        db: int = 0,
        password: Optional[str] = None,
        key_prefix: str = "memory",
    ):
        self.host = host
        self.port = port
        self.db = db
        self.password = password
        self.key_prefix = key_prefix

        self.redis: Optional[redis.Redis] = None
        self._connection_string = self._build_connection_string()

    def _build_connection_string(self) -> str:
        """Build Redis connection string for aioredis v2.x"""
        if self.password:
            return f"redis://:{self.password}@{self.host}:{self.port}/{self.db}"
        else:
            return f"redis://{self.host}:{self.port}/{self.db}"

    async def get_connection(self) -> redis.Redis:
        """Get Redis connection using redis-py async API."""
        if self.redis is None:
            try:
                # Use redis-py async API with connection string
                self.redis = redis.from_url(
                    self._connection_string,
                    decode_responses=True,
                    socket_connect_timeout=5,
                    socket_timeout=5,
                )
                # Test connection
                await self.redis.ping()
            except Exception as e:
                # Determine error type for better messaging
                error_type = (
                    "Connection timeout"
                    if "timeout" in str(e).lower() or "refused" in str(e).lower()
                    else str(e)
                )

                raise RuntimeError(
                    f"Failed to connect to Redis at {self.host}:{self.port}/{self.db}"
                    f"Error: {error_type}"
                    f"Please ensure Redis server is running and accessible."
                )
        return self.redis

    def make_key(self, key_type: str, *parts: str) -> str:
        """Create prefixed Redis key."""
        key_parts = [self.key_prefix, key_type] + list(parts)
        return ":".join(key_parts)

    async def initialize(self) -> bool:
        """Initialize Redis storage (test connection, create indices if needed)."""
        try:
            redis_conn = await self.get_connection()

            # Test connection
            await redis_conn.ping()

            # Initialize projects hash if doesn't exist
            projects_key = self.make_key("projects")
            if not await redis_conn.exists(projects_key):
                # Create empty hash with dummy key to initialize structure
                await redis_conn.hset(projects_key, "initialized", "true")

            return True

        except Exception as e:
            # Determine error type for better messaging
            error_type = (
                "Connection timeout"
                if "timeout" in str(e).lower() or "refused" in str(e).lower()
                else str(e)
            )

            logger.error(
                f"Redis initialization failed: Failed to connect to Redis at {self._connection_string}"
                f"Error: {error_type}"
                f"Please ensure Redis server is running and accessible."
            )
            # Raise exception for critical failures instead of returning False
            raise RuntimeError(
                f"Failed to connect to Redis at {self.host}:{self.port}/{self.db}"
                f"Error: {error_type}"
                f"Please ensure Redis server is running and accessible."
            )

    async def health_check(self) -> bool:
        """Check Redis connection health."""
        try:
            redis_conn = await self.get_connection()
            await redis_conn.ping()
            return True
        except Exception:
            return False

    async def close(self) -> None:
        """Close Redis connection."""
        if self.redis:
            await self.redis.aclose()
            self.redis = None
