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
Project utilities for Memory MCP Server

Utilities for working with project IDs, including normalization
and isolation management.
"""

from typing import Optional

from .config.config_loader import ConfigLoader


def normalize_project_id(project_id: Optional[str]) -> str:
    """
    Normalize project_id by replacing empty/None values with fallback project
    and standardizing naming format.

    This ensures proper project isolation by preventing empty project_id
    from accessing all projects. Empty values are replaced with the
    configured fallback project (default: "general").

    Additionally normalizes project names by:
    - Converting to lowercase for consistency
    - Replacing underscores and hyphens with spaces for unified naming
    - Trimming whitespace

    Args:
        project_id: Project ID that may be None, empty string, or whitespace

    Returns:
        Normalized project ID - either the original normalized value or fallback

    Examples:
        >>> normalize_project_id(None)
        'general'
        >>> normalize_project_id("")
        'general'
        >>> normalize_project_id("  ")
        'general'
        >>> normalize_project_id("My_Project")
        'my project'
        >>> normalize_project_id("extended-memory")
        'extended memory'
        >>> normalize_project_id("  SOME_PROJECT-NAME  ")
        'some project name'
    """
    if not project_id or project_id.strip() == "":
        config = ConfigLoader()
        return config.get_default("project_detection.fallback_project", "general")

    # Normalize the project ID format
    normalized = project_id.strip().lower()
    normalized = normalized.replace("_", " ").replace("-", " ")
    # Remove multiple spaces and trim
    normalized = " ".join(normalized.split())

    return normalized


def is_default_project(project_id: str) -> bool:
    """
    Check if project_id is the default/fallback project.

    Args:
        project_id: Project ID to check

    Returns:
        True if this is the default project, False otherwise
    """
    config = ConfigLoader()
    fallback_project = config.get_default("project_detection.fallback_project", "general")
    return project_id == fallback_project
