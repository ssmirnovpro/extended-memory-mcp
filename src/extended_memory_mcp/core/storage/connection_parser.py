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
Connection string parser for unified storage configuration.

Supports multiple storage providers through standardized connection strings:
- SQLite: sqlite:///path/to/database.db
- Redis: redis://host:port/database_number
- PostgreSQL: postgresql://user:password@host:port/database
"""

import os
import re
from pathlib import Path
from typing import Any, Dict, Optional
from urllib.parse import parse_qs, urlparse


class ConnectionStringError(Exception):
    """Raised when connection string parsing fails"""

    pass


class ConnectionStringParser:
    """Parse connection strings for different storage providers"""

    SUPPORTED_SCHEMES = {
        "sqlite": "sqlite",
        "redis": "redis",
        "postgresql": "postgresql",
        "postgres": "postgresql",  # alias
    }

    @classmethod
    def parse(cls, connection_string: str) -> Dict[str, Any]:
        """
        Parse connection string into provider config.

        Args:
            connection_string: URL-like connection string

        Returns:
            dict: {"provider": str, "config": dict}

        Raises:
            ConnectionStringError: If parsing fails or scheme unsupported

        Examples:
            sqlite:///~/.local/share/app/db.sqlite
            redis://localhost:6379/0
            postgresql://user:pass@localhost:5432/dbname
        """
        if not connection_string or not isinstance(connection_string, str):
            raise ConnectionStringError("Connection string cannot be empty")

        # Parse URL components
        try:
            parsed = urlparse(connection_string)
        except Exception as e:
            raise ConnectionStringError(f"Invalid URL format: {e}")

        scheme = parsed.scheme.lower()
        if not scheme:
            raise ConnectionStringError("Missing scheme in connection string")

        if scheme not in cls.SUPPORTED_SCHEMES:
            raise ConnectionStringError(
                f"Unsupported scheme '{scheme}'. "
                f"Supported: {list(cls.SUPPORTED_SCHEMES.keys())}"
            )

        provider = cls.SUPPORTED_SCHEMES[scheme]

        # Delegate to provider-specific parser
        if provider == "sqlite":
            config = cls._parse_sqlite(parsed)
        elif provider == "redis":
            config = cls._parse_redis(parsed)
        elif provider == "postgresql":
            config = cls._parse_postgresql(parsed)
        else:
            raise ConnectionStringError(f"No parser for provider '{provider}'")

        return {"provider": provider, "config": config}

    @classmethod
    def _parse_sqlite(cls, parsed) -> Dict[str, Any]:
        """Parse SQLite connection string"""
        # SQLite uses path as the main parameter
        # sqlite:///absolute/path or sqlite://relative/path

        if parsed.netloc:
            raise ConnectionStringError(
                "SQLite connection string should not have host/port. "
                "Use sqlite:///absolute/path or sqlite://relative/path"
            )

        path = parsed.path
        if not path:
            raise ConnectionStringError("SQLite connection string missing database path")

        # Handle triple slash correctly for absolute paths
        if path.startswith("/~/"):
            # Convert /~/path to ~/path for proper expansion
            path = path[1:]

        # Fix double slash for absolute paths (sqlite:/// creates /path instead of path)
        # But preserve the leading slash for absolute paths
        if path.startswith("//") and not path.startswith("/~/"):
            path = path[1:]  # Remove one leading slash

        # Expand user path (~) and environment variables
        path = os.path.expanduser(path)
        path = os.path.expandvars(path)

        # Validate path to prevent directory traversal attacks
        # Convert to absolute path and ensure it doesn't escape intended directories
        try:
            resolved_path = Path(path).resolve()
            # Basic validation: ensure path doesn't contain suspicious patterns
            if (
                ".." in str(resolved_path)
                or str(resolved_path).startswith("/etc/")
                or str(resolved_path).startswith("/var/")
            ):
                raise ValueError(f"Potentially unsafe database path: {path}")
            path = str(resolved_path)
        except (OSError, ValueError) as e:
            raise ValueError(f"Invalid database path: {path} - {e}")

        # Parse query parameters for additional options
        query_params = parse_qs(parsed.query)

        config = {
            "database_path": path,
            "timeout": cls._get_query_param(query_params, "timeout", 30.0, float),
            "check_same_thread": cls._get_query_param(
                query_params, "check_same_thread", True, bool
            ),
            "journal_mode": cls._get_query_param(query_params, "journal_mode", "WAL", str),
        }

        return config

    @classmethod
    def _parse_redis(cls, parsed) -> Dict[str, Any]:
        """Parse Redis connection string"""
        # redis://host:port/database_number?options

        host = parsed.hostname or "localhost"
        port = parsed.port or 6379

        # Database number from path (/0, /1, etc.)
        database = 0
        if parsed.path and parsed.path != "/":
            try:
                database = int(parsed.path.lstrip("/"))
            except ValueError:
                raise ConnectionStringError(f"Invalid Redis database number: {parsed.path}")

        # Parse query parameters
        query_params = parse_qs(parsed.query)

        config = {
            "host": host,
            "port": port,
            "database": database,
            "password": parsed.password,
            "username": parsed.username,
            "socket_timeout": cls._get_query_param(query_params, "socket_timeout", 30.0, float),
            "socket_connect_timeout": cls._get_query_param(
                query_params, "socket_connect_timeout", 30.0, float
            ),
            "retry_on_timeout": cls._get_query_param(query_params, "retry_on_timeout", True, bool),
            "max_connections": cls._get_query_param(query_params, "max_connections", 10, int),
        }

        # Remove None values for cleaner config
        return {k: v for k, v in config.items() if v is not None}

    @classmethod
    def _parse_postgresql(cls, parsed) -> Dict[str, Any]:
        """Parse PostgreSQL connection string"""
        # postgresql://user:password@host:port/database?options

        if not parsed.hostname:
            raise ConnectionStringError("PostgreSQL connection string missing hostname")

        if not parsed.path or parsed.path == "/":
            raise ConnectionStringError("PostgreSQL connection string missing database name")

        database = parsed.path.lstrip("/")
        query_params = parse_qs(parsed.query)

        config = {
            "host": parsed.hostname,
            "port": parsed.port or 5432,
            "database": database,
            "user": parsed.username,
            "password": parsed.password,
            "sslmode": cls._get_query_param(query_params, "sslmode", "prefer", str),
            "connect_timeout": cls._get_query_param(query_params, "connect_timeout", 30, int),
            "application_name": cls._get_query_param(
                query_params, "application_name", "extended-memory-mcp", str
            ),
        }

        # Remove None values for cleaner config
        return {k: v for k, v in config.items() if v is not None}

    @staticmethod
    def _get_query_param(query_params: Dict, key: str, default: Any, param_type: type) -> Any:
        """Extract and convert query parameter with default"""
        if key not in query_params:
            return default

        value = query_params[key][0]  # Take first value

        try:
            if param_type == bool:
                # Return True for truthy values, False for falsy values
                lower_val = value.lower()
                if lower_val in ("true", "1", "yes", "on"):
                    return True
                elif lower_val in ("false", "0", "no", "off"):
                    return False
                else:
                    # Invalid boolean string - return default
                    return default
            return param_type(value)
        except (ValueError, TypeError):
            return default

    @classmethod
    def get_default_connection_string(cls) -> str:
        """Get default SQLite connection string for this platform"""
        from ..config import get_env_default

        # Get default from STORAGE_CONNECTION_STRING env/config
        default_connection = get_env_default(
            "STORAGE_CONNECTION_STRING", "sqlite:///~/.local/share/extended-memory-mcp/memory.db"
        )

        # If it's already a full connection string, return as is
        if "://" in default_connection:
            # Expand user path if needed
            if default_connection.startswith("sqlite:///~"):
                expanded_path = os.path.expanduser(default_connection[10:])  # Remove 'sqlite:///'
                return f"sqlite:///{expanded_path}"
            return default_connection
        else:
            # Treat as path, expand and format as sqlite connection
            expanded_path = os.path.expanduser(default_connection)
            return f"sqlite:///{expanded_path}"

    @classmethod
    def validate_connection_string(cls, connection_string: str) -> bool:
        """Validate connection string without throwing exceptions"""
        try:
            cls.parse(connection_string)
            return True
        except (ConnectionStringError, ValueError, TypeError):
            return False
