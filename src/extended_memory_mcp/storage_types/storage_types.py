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
Standardized storage types for cross-provider compatibility.

These TypedDict definitions ensure consistent data structures between
SQLite, Redis, and future storage providers. This provides type safety
and clear contracts for all storage operations.
"""

from datetime import datetime
from typing import Any, Dict, List, Optional, TypedDict


class ContextData(TypedDict, total=False):
    """
    Standard context data structure returned by all storage providers.

    Used by: save_context, load_context, load_contexts, search_contexts
    """

    id: str  # Context identifier (string for compatibility across providers)
    content: str  # Context content text
    importance_level: int  # 1-10 importance rating
    project_id: Optional[str]  # Project isolation (None for global)
    tags: List[str]  # Associated tags list
    created_at: str  # ISO format timestamp
    expires_at: Optional[str]  # ISO format expiry (optional)
    status: str  # Context status (active, archived, expired)


class ProjectInfo(TypedDict, total=False):
    """
    Standard project information structure.

    Used by: list_projects, list_all_projects_global
    """

    id: str  # Project identifier
    name: str  # Human-readable project name
    description: Optional[str]  # Project description
    last_accessed: str  # ISO format timestamp
    context_count: int  # Number of contexts in project
    status: str  # Project status (active, archived, completed)


class PopularTag(TypedDict):
    """
    Popular tag with usage statistics.

    Used by: get_popular_tags
    """

    tag: str  # Tag name
    count: int  # Usage count across contexts


class TagInfo(TypedDict, total=False):
    """
    Extended tag information with metadata.

    Used by: analytics and tag management functions
    """

    tag: str  # Tag name
    count: int  # Usage count
    project_id: Optional[str]  # Associated project (if any)
    last_used: str  # ISO format timestamp
    contexts: List[str]  # Context IDs using this tag


class SearchFilters(TypedDict, total=False):
    """
    Standardized search filter parameters.

    Used by: search_contexts and complex query operations
    """

    project_id: Optional[str]  # Filter by project
    tags_filter: Optional[List[str]]  # Filter by tags (OR logic)
    content_search: Optional[
        str
    ]  # Text search in content (RESERVED: for future advanced search features)
    min_importance: Optional[int]  # Minimum importance level
    max_importance: Optional[int]  # Maximum importance level
    created_after: Optional[str]  # ISO format date filter
    created_before: Optional[str]  # ISO format date filter
    status: Optional[str]  # Filter by context status
    limit: Optional[int]  # Maximum results to return
    offset: Optional[int]  # Results offset for pagination


class StorageStats(TypedDict):
    """
    Storage provider statistics and metrics.

    Used by: get_storage_stats
    """

    total_contexts: int  # Total number of contexts
    total_projects: int  # Total number of projects
    total_tags: int  # Total number of unique tags
    storage_size_bytes: Optional[int]  # Storage size (if available)
    active_contexts: int  # Contexts with active status
    archived_contexts: int  # Contexts with archived status
    expired_contexts: int  # Contexts with expired status
    avg_importance: float  # Average importance level
    provider_type: str  # Storage provider name (sqlite, redis, etc.)
    last_cleanup: Optional[str]  # ISO format timestamp of last cleanup


class InitContextsResult(TypedDict):
    """
    Result structure for session initialization.

    Used by: load_init_contexts
    """

    init_instruction: str  # System initialization instruction
    contexts: List[ContextData]  # Recent/relevant contexts
    total_contexts: int  # Total number of contexts available
    project_info: Optional[ProjectInfo]  # Current project information


# Type aliases for backward compatibility
ContextDict = Dict[str, Any]  # Legacy context dictionary
ProjectDict = Dict[str, Any]  # Legacy project dictionary
TagDict = Dict[str, Any]  # Legacy tag dictionary

# Union types for flexibility
StorageResult = Optional[Dict[str, Any]]  # Generic storage operation result
ContextList = List[ContextData]  # List of contexts
ProjectList = List[ProjectInfo]  # List of projects
TagList = List[PopularTag]  # List of tags
