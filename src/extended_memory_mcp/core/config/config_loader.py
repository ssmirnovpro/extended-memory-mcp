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
Configuration loader for Memory MCP Server

Centralized loading of configuration from /config/memory_config.yaml
with fallback to hardcoded defaults for compatibility.
"""

import logging
import os
from pathlib import Path
from typing import Any, Dict, Optional

import yaml

logger = logging.getLogger(__name__)


class ConfigLoader:
    """Centralized configuration loader with fallback defaults."""

    _instance: Optional["ConfigLoader"] = None
    _config: Optional[Dict[str, Any]] = None

    def __new__(cls) -> "ConfigLoader":
        """Singleton pattern for configuration."""
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self):
        """Initialize config loader."""
        if self._config is None:
            self._config = self._load_config()

    def _get_config_path(self) -> Path:
        """Get path to configuration file."""
        # Look for config in project root
        current_dir = Path(__file__).parent
        project_root = current_dir.parent.parent.parent  # Go up from mcp-server/core/config/
        config_path = project_root / "config" / "memory_config.yaml"

        # Fallback to old location for compatibility
        if not config_path.exists():
            old_config_path = current_dir.parent.parent / "config" / "memory_config.yaml"
            if old_config_path.exists():
                logger.warning(f"Using old config location: {old_config_path}")
                return old_config_path

        return config_path

    def _load_config(self) -> Dict[str, Any]:
        """Load configuration from YAML file with fallback defaults."""
        config_path = self._get_config_path()

        # Hardcoded fallback defaults (for compatibility)
        fallback_defaults = {
            "defaults": {
                "storage": {
                    "sqlite_default_path": "~/.local/share/extended-memory-mcp/memory.db",
                    "connection_timeout": 30.0,
                    "redis_key_prefix": "extended_memory",
                    "redis_ttl_hours": 8760,
                    "redis_socket_timeout": 30.0,
                    "redis_max_connections": 10,
                },
                "logging": {
                    "level": "INFO",
                    "format": "%(asctime)s - %(name)s - %(levelname)s - %(message)s",
                },
                "server": {
                    "name": "extended-memory",
                    "version": "1.0.0",
                    "description": "Persistent memory for cross-chat interactions",
                    "mcp_timeout": 30.0,
                },
                "memory": {
                    "default_importance_threshold": 5,
                    "max_search_results": 20,
                    "similarity_threshold": 0.8,
                },
            }
        }

        try:
            if config_path.exists():
                with open(config_path, "r", encoding="utf-8") as f:
                    yaml_config = yaml.safe_load(f) or {}

                # Merge with fallback defaults
                config = self._deep_merge(fallback_defaults, yaml_config)
                logger.info(f"Configuration loaded from: {config_path}")
                return config
            else:
                logger.warning(f"Config file not found at {config_path}, using fallback defaults")
                return fallback_defaults

        except Exception as e:
            logger.error(f"Error loading config from {config_path}: {e}")
            logger.warning("Using fallback defaults")
            return fallback_defaults

    def _deep_merge(self, base: Dict[str, Any], override: Dict[str, Any]) -> Dict[str, Any]:
        """Deep merge two dictionaries."""
        result = base.copy()

        for key, value in override.items():
            if key in result and isinstance(result[key], dict) and isinstance(value, dict):
                result[key] = self._deep_merge(result[key], value)
            else:
                result[key] = value

        return result

    def get_env_default(self, env_var_name: str, fallback: Any = None) -> Any:
        """
        Get environment variable with fallback to config defaults.

        Args:
            env_var_name: Environment variable name (e.g., 'STORAGE_CONNECTION_STRING')
            fallback: Fallback value if neither env nor config has the value

        Returns:
            Environment variable value, config default, or fallback

        Example:
            >>> config = ConfigLoader()
            >>> conn_str = config.get_env_default('STORAGE_CONNECTION_STRING')
            >>> log_level = config.get_env_default('LOG_LEVEL')
        """
        import os

        # First check environment variable
        env_value = os.getenv(env_var_name)
        if env_value is not None and env_value.strip():  # Don't accept empty strings
            return env_value

        # Then check config file top-level
        config_value = self._config.get(env_var_name)
        if config_value is not None:
            return config_value

        # Finally return fallback
        return fallback

    def get_default(self, key_path: str, fallback: Any = None) -> Any:
        """
        Get default value by dot-separated key path.

        Args:
            key_path: Dot-separated path like 'storage.sqlite_default_path'
            fallback: Fallback value if key not found

        Returns:
            Configuration value or fallback

        Example:
            >>> config = ConfigLoader()
            >>> path = config.get_default('storage.sqlite_default_path')
            >>> prefix = config.get_default('storage.redis_key_prefix')
        """
        try:
            keys = key_path.split(".")
            current = self._config.get("defaults", {})

            for key in keys:
                if isinstance(current, dict) and key in current:
                    current = current[key]
                else:
                    return fallback

            return current
        except Exception as e:
            logger.warning(f"Error getting default for '{key_path}': {e}")
            return fallback

    def get_config_section(self, section: str) -> Dict[str, Any]:
        """
        Get entire configuration section.

        Args:
            section: Section name like 'storage', 'logging', etc.

        Returns:
            Configuration section dict
        """
        return self._config.get(section, {})

    def get_runtime_config(self, section: str, key: str, default_path: str = None) -> Any:
        """
        Get runtime config value with fallback to defaults.

        Args:
            section: Config section (storage, logging, etc.)
            key: Config key
            default_path: Path to default value (defaults to section.key)

        Returns:
            Runtime config value or default
        """
        # Try runtime config first
        runtime_section = self._config.get(section, {})
        if key in runtime_section:
            return runtime_section[key]

        # Fallback to defaults
        if default_path is None:
            default_path = f"{section}.{key}"

        return self.get_default(default_path)


# Global instance
_config_loader = None


def get_config_loader() -> ConfigLoader:
    """Get global configuration loader instance."""
    global _config_loader
    if _config_loader is None:
        _config_loader = ConfigLoader()
    return _config_loader


def get_env_default(env_var_name: str, fallback: Any = None) -> Any:
    """Convenience function to get environment variable with config fallback."""
    return get_config_loader().get_env_default(env_var_name, fallback)


def get_default(key_path: str, fallback: Any = None) -> Any:
    """Convenience function to get default value."""
    return get_config_loader().get_default(key_path, fallback)


def get_config_section(section: str) -> Dict[str, Any]:
    """Convenience function to get config section."""
    return get_config_loader().get_config_section(section)


def get_runtime_config(section: str, key: str, default_path: str = None) -> Any:
    """Convenience function to get runtime config with defaults."""
    return get_config_loader().get_runtime_config(section, key, default_path)
