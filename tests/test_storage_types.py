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
Test new storage types integration.
"""

import pytest
import sys
import os

# Add mcp-server directory to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "mcp-server"))

from extended_memory_mcp.storage_types.storage_types import (
    ContextData,
    PopularTag,
    ProjectInfo,
    SearchFilters,
    StorageStats,
    InitContextsResult,
)


class TestStorageTypes:
    """Test storage types structure and validation."""

    def test_context_data_structure(self):
        """Test ContextData structure."""
        context: ContextData = {
            "id": "ctx_123",
            "content": "Test content",
            "importance_level": 8,
            "project_id": "test_project",
            "tags": ["test", "types"],
            "created_at": "2025-07-05T23:00:00Z",
            "status": "active"
        }
        
        assert context["id"] == "ctx_123"
        assert context["importance_level"] == 8
        assert isinstance(context["tags"], list)

    def test_popular_tag_structure(self):
        """Test PopularTag structure."""
        tag: PopularTag = {
            "tag": "redis",
            "count": 15
        }
        
        assert tag["tag"] == "redis"
        assert tag["count"] == 15

    def test_project_info_structure(self):
        """Test ProjectInfo structure."""
        project: ProjectInfo = {
            "id": "extended_memory",
            "name": "Extended Memory MCP",
            "description": "AI memory system",
            "last_accessed": "2025-07-05T23:00:00Z",
            "context_count": 447,
            "status": "active"
        }
        
        assert project["id"] == "extended_memory"
        assert project["context_count"] == 447

    def test_search_filters_structure(self):
        """Test SearchFilters structure."""
        filters: SearchFilters = {
            "project_id": "test_project",
            "tags_filter": ["redis", "performance"],
            "min_importance": 7,
            "limit": 20
        }
        
        assert filters["project_id"] == "test_project"
        assert len(filters["tags_filter"]) == 2

    def test_storage_stats_structure(self):
        """Test StorageStats structure."""
        stats: StorageStats = {
            "total_contexts": 447,
            "total_projects": 5,
            "total_tags": 50,
            "active_contexts": 440,
            "archived_contexts": 7,
            "expired_contexts": 0,
            "avg_importance": 7.2,
            "provider_type": "sqlite"
        }
        
        assert stats["total_contexts"] == 447
        assert stats["provider_type"] == "sqlite"

    def test_init_contexts_result_structure(self):
        """Test InitContextsResult structure."""
        result: InitContextsResult = {
            "init_instruction": "Session initialization guide...",
            "contexts": [],
            "total_contexts": 447
        }
        
        assert "init_instruction" in result
        assert isinstance(result["contexts"], list)
        assert result["total_contexts"] == 447
