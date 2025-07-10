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
Storage Factory - Creates storage providers based on configuration.

Uses connection strings for unified storage configuration:
- STORAGE_CONNECTION_STRING environment variable (preferred)
- Config file fallback
- Platform defaults
"""

import logging
import os
from pathlib import Path
from typing import Any, Dict, Optional

from .connection_parser import ConnectionStringError, ConnectionStringParser
from .interfaces.storage_provider import IStorageProvider

# Module-level logger
logger = logging.getLogger("StorageFactory")


class StorageFactory:
    """
    Factory for creating storage provider instances based on connection strings.

    Priority order:
    1. STORAGE_CONNECTION_STRING environment variable
    2. Config file settings
    3. Default connection string for platform
    """

    @staticmethod
    def get_connection_string() -> str:
        """
        Get connection string from environment or config, with fail-fast validation.

        IMPORTANT: No silent fallbacks to prevent data integrity issues.
        If Redis is configured but fails, we crash instead of falling back to SQLite.

        Returns:
            Connection string ready for parsing
        """
        # 1. Check environment variable first (primary method for production)
        env_connection = os.getenv("STORAGE_CONNECTION_STRING")
        if env_connection:
            return env_connection

        # 2. Use development default with explicit logging
        # This ensures developers can start quickly, but production must be explicit
        default_connection = ConnectionStringParser.get_default_connection_string()

        # Log default usage to make it visible
        logger.warning(
            f"No STORAGE_CONNECTION_STRING configured, using development default: {default_connection}"
        )
        logger.warning(
            "For production, set STORAGE_CONNECTION_STRING environment variable to explicit path"
        )
        logger.warning("Example: STORAGE_CONNECTION_STRING='sqlite:///~/my-app/memory.db'")

        return default_connection

    @staticmethod
    async def create_provider(connection_string_override: Optional[str] = None) -> IStorageProvider:
        """
        Create storage provider based on connection string.

        Args:
            connection_string_override: Override connection string for testing

        Returns:
            Initialized storage provider instance

        Raises:
            ValueError: If connection string is invalid
            RuntimeError: If provider initialization fails
        """
        # Get connection string
        connection_string = connection_string_override or StorageFactory.get_connection_string()

        # Parse connection string
        try:
            parsed = ConnectionStringParser.parse(connection_string)
        except ConnectionStringError as e:
            raise ValueError(f"Invalid connection string: {e}")

        provider_name = parsed["provider"]
        config = parsed["config"]

        # Use logger instead of print to avoid MCP JSON corruption
        logger.info(f"Creating storage provider: {provider_name}")
        logger.info(f"Connection: {connection_string}")

        # Create provider based on type - FAIL FAST if configuration is wrong
        try:
            if provider_name == "sqlite":
                return await StorageFactory._create_sqlite_provider(config, logger)
            elif provider_name == "redis":
                return await StorageFactory._create_redis_provider(config, logger)
            elif provider_name == "postgresql":
                return await StorageFactory._create_postgresql_provider(config, logger)
            else:
                raise ValueError(f"Unsupported storage provider: {provider_name}")
        except Exception as e:
            # CRITICAL: No silent fallbacks. If provider fails, crash immediately
            logger.error(f"FATAL: Storage provider '{provider_name}' initialization failed")
            logger.error(f"Connection string: {connection_string}")
            logger.error(f"Error: {e}")
            logger.error("Fix the configuration or check service availability")
            logger.error("NO FALLBACK TO PREVENT DATA INTEGRITY ISSUES")
            raise RuntimeError(f"Storage provider '{provider_name}' failed: {e}") from e

    @staticmethod
    async def _create_sqlite_provider(config: Dict[str, Any], logger) -> IStorageProvider:
        """Create SQLite provider from parsed connection config"""
        from .providers.sqlite.sqlite_provider import SQLiteStorageProvider

        db_path = config["database_path"]

        # Create directory if it doesn't exist
        db_dir = Path(db_path).parent
        db_dir.mkdir(parents=True, exist_ok=True)

        provider = SQLiteStorageProvider(
            db_path=db_path,
            timeout=config.get("timeout", 30.0),
            check_same_thread=config.get("check_same_thread", True),
        )

        if await provider.initialize():
            logger.info(f"SQLite provider initialized: {db_path}")
            return provider
        else:
            raise RuntimeError(f"Failed to initialize SQLite provider at {db_path}")

    @staticmethod
    async def _create_redis_provider(config: Dict[str, Any], logger) -> IStorageProvider:
        """Create Redis provider from parsed connection config with compatibility checks"""
        try:
            from .providers.redis.redis_provider import (
                REDIS_AVAILABLE,
                REDIS_VERSION_ERROR,
                RedisStorageProvider,
            )

            if not REDIS_AVAILABLE:
                error_msg = (
                    "Redis storage provider is not available.\n"
                    "To use Redis storage, install the Redis extra:\n"
                    "  pip install extended-memory-mcp[redis]\n"
                    "Or install aioredis directly:\n"
                    "  pip install 'aioredis>=2.0.0,<3.0.0'"
                )
                if REDIS_VERSION_ERROR:
                    error_msg += f"\nError details: {REDIS_VERSION_ERROR}"

                logger.error(error_msg)
                raise ImportError(error_msg)

            # Use environment overrides for Redis-specific settings, fallback to config defaults
            from ..config import get_env_default

            key_prefix = get_env_default("REDIS_KEY_PREFIX", "extended_memory")
            ttl_hours = int(get_env_default("REDIS_TTL_HOURS", 8760))

            provider = RedisStorageProvider(
                host=config["host"],
                port=config["port"],
                db=config["database"],
                password=config.get("password"),
                key_prefix=key_prefix,
                ttl_hours=ttl_hours,
            )

            # Test connection during creation
            if await provider.initialize():
                logger.info(
                    f"Redis provider initialized: {config['host']}:{config['port']}/{config['database']}"
                )
                return provider
            else:
                raise RuntimeError(
                    f"Failed to initialize Redis provider at {config['host']}:{config['port']}"
                )

        except ImportError:
            # Re-raise ImportError with helpful message
            raise
        except Exception as e:
            error_msg = (
                f"Failed to create Redis provider: {e}\n"
                f"Connection: {config['host']}:{config['port']}/{config['database']}\n"
                "Please check:\n"
                "  1. Redis server is running\n"
                "  2. Connection parameters are correct\n"
                "  3. Network connectivity to Redis server"
            )
            logger.error(error_msg)
            raise RuntimeError(error_msg)

    @staticmethod
    async def _create_postgresql_provider(config: Dict[str, Any], logger) -> IStorageProvider:
        """Create PostgreSQL provider from parsed connection config"""
        # Future implementation when PostgreSQL provider is ready
        raise NotImplementedError(
            "PostgreSQL provider not yet implemented. " f"Config received: {config}"
        )

    @staticmethod
    def validate_connection_string(connection_string: str) -> bool:
        """
        Validate connection string without creating provider.

        Args:
            connection_string: Connection string to validate

        Returns:
            True if valid, False otherwise
        """
        return ConnectionStringParser.validate_connection_string(connection_string)

    @staticmethod
    def get_provider_info(connection_string: Optional[str] = None) -> Dict[str, Any]:
        """
        Get provider information without creating instance.

        Args:
            connection_string: Optional connection string override

        Returns:
            Dict with provider info: {"provider": str, "config": dict}
        """
        conn_str = connection_string or StorageFactory.get_connection_string()

        try:
            return ConnectionStringParser.parse(conn_str)
        except ConnectionStringError as e:
            return {"provider": "unknown", "config": {}, "error": str(e)}


# Convenience function for quick provider creation
async def get_storage_provider() -> IStorageProvider:
    """
    Get storage provider using connection string configuration.

    Usage:
        provider = await get_storage_provider()
        context_id = await provider.save_context(...)
    """
    return await StorageFactory.create_provider()
