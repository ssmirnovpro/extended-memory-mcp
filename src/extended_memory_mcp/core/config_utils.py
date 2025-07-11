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
Configuration utilities for Memory MCP Server
Centralized configuration management
"""

from __future__ import annotations

import logging
from pathlib import Path

import yaml

logger = logging.getLogger(__name__)

# Single source of truth for config file path
try:
    MEMORY_CONFIG_PATH = Path(__file__).parent.parent.parent / "config" / "memory_config.yaml"
except Exception:
    # Fallback for edge cases in CI/tests
    MEMORY_CONFIG_PATH = Path("config") / "memory_config.yaml"


def load_memory_config() -> Dict[str, Any]:
    """
    Load memory configuration from YAML file
    Returns empty dict if file not found or invalid
    """
    try:
        if MEMORY_CONFIG_PATH.exists():
            with open(MEMORY_CONFIG_PATH, "r", encoding="utf-8") as f:
                return yaml.safe_load(f) or {}
    except Exception as e:
        # Silently fail and return empty config
        logger.warning(
            f"Could not open or parse the memory config file at {MEMORY_CONFIG_PATH}: {e}"
        )
    return {}
