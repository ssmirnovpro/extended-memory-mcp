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
Tool Descriptions Loader

Loads tool descriptions from external markdown files for better maintainability.
"""

import json
import logging
from pathlib import Path
from typing import Dict, Optional


class ToolDescriptionsLoader:
    """Loads tool descriptions from external markdown files"""

    def __init__(self, config_dir: Optional[Path] = None):
        """
        Initialize descriptions loader.

        Args:
            config_dir: Base config directory (optional, auto-detected if not provided)
        """
        if config_dir is None:
            # Auto-detect config directory relative to this file
            self.config_dir = Path(__file__).parent
        else:
            self.config_dir = config_dir

        self.descriptions_dir = self.config_dir / "descriptions"
        self.schemas_file = self.config_dir / "schema" / "input_schemas.json"
        self.logger = logging.getLogger("MemoryMCP.DescriptionsLoader")

        # Cache for loaded descriptions
        self._descriptions_cache = {}
        self._schemas_cache = None

    def load_tool_description(self, tool_name: str) -> str:
        """
        Load tool description from markdown file.

        Args:
            tool_name: Name of the tool to load description for

        Returns:
            Tool description text

        Raises:
            Exception: If description file not found or cannot be parsed
        """
        if tool_name in self._descriptions_cache:
            return self._descriptions_cache[tool_name]

        description_file = self.descriptions_dir / f"{tool_name}.md"

        if not description_file.exists():
            raise FileNotFoundError(f"Description file not found: {description_file}")

        try:
            description = self._parse_markdown_description(description_file)
            self._descriptions_cache[tool_name] = description
            return description
        except Exception as e:
            self.logger.error(f"Error loading description for {tool_name}: {e}")
            raise

    def _parse_markdown_description(self, file_path: Path) -> str:
        """
        Parse markdown file and extract description.

        Returns the entire content of the file.

        Args:
            file_path: Path to the markdown file

        Returns:
            Full description text from the file
        """
        try:
            content = file_path.read_text(encoding="utf-8")
            return content.strip()

        except Exception as e:
            self.logger.error(f"Error parsing markdown file {file_path}: {e}")
            raise

    def load_input_schemas(self) -> Dict:
        """
        Load input schemas from JSON file.

        Returns:
            Dictionary of input schemas for all tools

        Raises:
            Exception: If schemas file not found or cannot be parsed
        """
        if self._schemas_cache is not None:
            return self._schemas_cache

        if not self.schemas_file.exists():
            raise FileNotFoundError(f"Schemas file not found: {self.schemas_file}")

        try:
            with open(self.schemas_file, "r", encoding="utf-8") as f:
                schemas = json.load(f)
                self._schemas_cache = schemas
                return schemas
        except Exception as e:
            self.logger.error(f"Error loading input schemas: {e}")
            raise

    def get_tool_schema(self, tool_name: str) -> Dict:
        """
        Get input schema for specific tool.

        Args:
            tool_name: Name of the tool

        Returns:
            Input schema for the tool

        Raises:
            KeyError: If tool schema not found
        """
        schemas = self.load_input_schemas()
        if tool_name not in schemas:
            raise KeyError(f"Schema not found for tool: {tool_name}")
        return schemas[tool_name]


def create_tool_descriptions_loader(config_dir: Optional[Path] = None) -> ToolDescriptionsLoader:
    """
    Factory function to create tool descriptions loader.

    Args:
        config_dir: Base config directory (optional, auto-detected if not provided)

    Returns:
        Configured ToolDescriptionsLoader instance
    """
    return ToolDescriptionsLoader(config_dir)
