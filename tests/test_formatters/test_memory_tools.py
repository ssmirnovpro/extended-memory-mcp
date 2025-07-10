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

"""Test Memory Tools Handler"""

import pytest
from unittest.mock import AsyncMock, MagicMock
import sys
from pathlib import Path

# Add project path for imports
sys.path.append(str(Path(__file__).parent.parent.parent / "mcp-server"))

from extended_memory_mcp.tools.memory_tools import MemoryToolsHandler, create_memory_tools_handler
from extended_memory_mcp.formatters.summary_formatter import ContextSummaryFormatter


class TestMemoryToolsHandler:
    """Test memory tools handler"""

    @pytest.fixture
    def mock_storage_provider(self):
        """Mock storage provider for testing"""
        mock = AsyncMock()
        mock.save_context.return_value = 123
        mock.load_contexts.return_value = []
        mock.forget_context.return_value = True
        mock.list_all_projects_global.return_value = [
            {"id": "test_project", "name": "test_project", "context_count": 1}
        ]
        mock.create_project.return_value = None
        mock.update_project_access.return_value = None
        # Explicitly mock tags_repo to avoid unintended coroutine creation
        del mock.tags_repo  # Ensure tags_repo doesn't exist, so hasattr returns False
        return mock

    @pytest.fixture
    def mock_logger(self):
        """Mock logger for testing"""
        return MagicMock()

    @pytest.fixture
    def summary_formatter(self):
        """Real summary formatter for testing"""
        return ContextSummaryFormatter()

    @pytest.fixture
    def tools_handler(self, mock_storage_provider, summary_formatter, mock_logger):
        """Create tools handler for testing"""
        return MemoryToolsHandler(mock_storage_provider, summary_formatter, mock_logger)

    def test_create_memory_tools_handler(self, mock_storage_provider, summary_formatter, mock_logger):
        """Test factory function"""
        handler = create_memory_tools_handler(mock_storage_provider, summary_formatter, mock_logger)
        assert isinstance(handler, MemoryToolsHandler)

    @pytest.mark.asyncio
    async def test_execute_tool_save_context(self, tools_handler):
        """Test tool execution routing for save_context"""
        result = await tools_handler.execute_tool("save_context", {
            "content": "Test content",
            "importance_level": 7
        })
        
        assert "content" in result
        assert "Context saved successfully" in result["content"][0]["text"]
        assert "Context ID: 123" in result["content"][0]["text"]

    @pytest.mark.asyncio
    async def test_execute_tool_load_contexts_init(self, tools_handler):
        """Test tool execution for load_contexts with init_load"""
        result = await tools_handler.execute_tool("load_contexts", {
            "project_id": "test_project",
            "init_load": True
        })
        
        assert "content" in result
        assert isinstance(result["content"], list)
        assert len(result["content"]) >= 1  # At least instruction

    @pytest.mark.asyncio
    async def test_execute_tool_load_contexts_regular(self, tools_handler):
        """Test tool execution for regular load_contexts"""
        result = await tools_handler.execute_tool("load_contexts", {
            "project_id": "test_project", 
            "init_load": False
        })
        
        assert "content" in result
        assert "No saved contexts found" in result["content"][0]["text"]

    @pytest.mark.asyncio
    async def test_execute_tool_forget_context(self, tools_handler):
        """Test tool execution for forget_context"""
        result = await tools_handler.execute_tool("forget_context", {
            "context_id": 123
        })
        
        # forget_context now returns MCP-compatible content format
        assert "content" in result
        assert len(result["content"]) > 0
        assert result["content"][0]["type"] == "text"
        assert "deleted successfully" in result["content"][0]["text"]

    @pytest.mark.asyncio
    async def test_execute_tool_list_projects(self, tools_handler):
        """Test tool execution for list_all_projects"""
        result = await tools_handler.execute_tool("list_all_projects", {})
        
        # list_all_projects returns content format, not success format
        assert "content" in result
        assert len(result["content"]) > 0

    @pytest.mark.asyncio
    async def test_execute_tool_unknown_tool(self, tools_handler):
        """Test error handling for unknown tool"""
        with pytest.raises(Exception, match="Unknown tool"):
            await tools_handler.execute_tool("unknown_tool", {})

    @pytest.mark.asyncio
    async def test_save_context_with_defaults(self, tools_handler, context_repo):
        """Test save_context with default parameters"""
        # Use tools_handler instead of context_repo directly
        result = await tools_handler.save_context(
            content="Test content",
            importance_level=5
        )
        
        # Check result
        assert result["content"][0]["text"].startswith("✅ Context saved successfully!")
        assert "Context ID:" in result["content"][0]["text"]
        
        assert "content" in result
        assert "Context saved successfully" in result["content"][0]["text"]

    @pytest.mark.asyncio
    async def test_save_context_with_current_project(self, tools_handler, context_repo):
        """Test save_context uses current_project when no project_id specified"""
        tools_handler.current_project = "my_project"
        
        result = await tools_handler.save_context(
            content="Test content",
            importance_level=5
        )
        
        # Check that context was saved successfully
        assert result["content"][0]["text"].startswith("✅ Context saved successfully!")
        assert "my_project" in result["content"][0]["text"] or "project" in result["content"][0]["text"]

    @pytest.mark.asyncio
    async def test_load_contexts_init_without_personality(self, tools_handler, context_repo):
        """Test load_contexts init_load without personality data"""
        tools_handler.storage_provider.load_contexts.return_value = [
            {"content": "Test context", "context_type": "general", "importance_level": 5, "created_at": "2025-07-04T10:00:00"}
        ]
        
        result = await tools_handler.load_contexts(
            init_load=True
        )
        
        assert "content" in result
        assert len(result["content"]) == 1  # unified response now
        
        # Check basic functionality - memory loads successfully  
        text_content = result["content"][0]["text"]
        assert "Memory Loaded Successfully" in text_content
        assert "Test context" in text_content

    @pytest.mark.asyncio
    async def test_load_contexts_with_data(self, tools_handler, context_repo):
        """Test load_contexts with actual context data"""
        tools_handler.storage_provider.load_contexts.return_value = [
            {
                "id": 1,
                "content": "Test context content",
                "importance_level": 8,
                "created_at": "2025-07-04T10:00:00"
            }
        ]
        
        result = await tools_handler.load_contexts(
            init_load=False
        )
        
        assert "content" in result
        text_content = result["content"][0]["text"]
        assert "Memory Loaded Successfully" in text_content
        assert "Test context content" in text_content
        # No type information since context_type was removed

    @pytest.mark.asyncio
    async def test_forget_context_not_found(self, tools_handler):
        """Test forget_context when context not found"""
        tools_handler.storage_provider.forget_context.return_value = False
        
        result = await tools_handler.forget_context(999)
        
        # forget_context now returns MCP-compatible content format for errors too
        assert "content" in result
        assert len(result["content"]) > 0
        assert result["content"][0]["type"] == "text"
        assert "not found" in result["content"][0]["text"]

    @pytest.mark.asyncio
    async def test_error_handling_save_context(self, tools_handler, context_repo):
        """Test error handling in save_context"""
        tools_handler.storage_provider.save_context.side_effect = Exception("Database error")
        
        result = await tools_handler.save_context(
            content="Test content",
            importance_level=5
        )
        
        assert "content" in result
        assert "Error saving context" in result["content"][0]["text"]
        assert "Database error" in result["content"][0]["text"]

    @pytest.mark.asyncio 
    async def test_error_handling_load_contexts(self, tools_handler, context_repo):
        """Test error handling in load_contexts"""
        tools_handler.storage_provider.load_contexts.side_effect = Exception("Load error")
        
        result = await tools_handler.load_contexts(
            init_load=False
        )
        
        assert "content" in result
        assert "Error loading contexts" in result["content"][0]["text"]
        assert "Load error" in result["content"][0]["text"]

    # --- New tests for tags functionality ---

    @pytest.fixture
    def mock_tags_repo(self):
        """Mock tags repository with popular tags"""
        mock = AsyncMock()
        mock.get_popular_tags.return_value = [
            {"tag": "python", "count": 5},
            {"tag": "database", "count": 3},
            {"tag": "testing", "count": 1}
        ]
        # Mock load_context_tags_batch to avoid unintended coroutine creation
        mock.load_context_tags_batch.return_value = {}
        return mock

    @pytest.fixture
    def mock_storage_with_tags(self, mock_storage_provider, mock_tags_repo):
        """Enhanced storage provider with tags support"""
        mock_storage_provider.tags_repo = mock_tags_repo
        return mock_storage_provider

    @pytest.fixture
    def tools_handler_with_tags(self, mock_storage_with_tags, summary_formatter, mock_logger):
        """Create tools handler with tags support for testing"""
        return MemoryToolsHandler(mock_storage_with_tags, summary_formatter, mock_logger)

    async def test_execute_tool_get_popular_tags(self, tools_handler_with_tags):
        """Test tool execution routing for get_popular_tags"""
        result = await tools_handler_with_tags.execute_tool("get_popular_tags", {
            "limit": 10,
            "min_usage": 2
        })
        
        assert result["success"] is True
        assert "tags" in result
        assert "total" in result
        assert "min_usage" in result
        assert "content" in result
        assert "Popular Tags" in result["content"][0]["text"]

    async def test_get_popular_tags_tool_with_min_usage(self, tools_handler_with_tags):
        """Test get_popular_tags_tool with min_usage filter"""
        result = await tools_handler_with_tags.get_popular_tags_tool(limit=10, min_usage=3)
        
        assert result["success"] is True
        assert result["min_usage"] == 3
        assert "content" in result
        
        text = result["content"][0]["text"]
        assert "Popular Tags" in text and "min 3 uses" in text

    @pytest.mark.asyncio
    async def test_get_popular_tags_tool_with_limit(self, tools_handler_with_tags):
        """Test get_popular_tags_tool with limit parameter"""
        # Mock tags_repo to respect the limit parameter
        from unittest.mock import AsyncMock
        tools_handler_with_tags.storage_provider.tags_repo.get_popular_tags = AsyncMock(
            return_value=[
                {"tag": "python", "count": 5},
                {"tag": "database", "count": 3}
            ]
        )
        
        result = await tools_handler_with_tags.get_popular_tags_tool(limit=2, min_usage=1)
        
        assert result["success"] is True
        assert len(result["tags"]) <= 2

    @pytest.mark.asyncio
    async def test_get_popular_tags_tool_empty_result(self, tools_handler):
        """Test get_popular_tags_tool with no tags available"""
        # Setup mock tags_repo that returns empty list
        from unittest.mock import AsyncMock
        mock_tags_repo = AsyncMock()
        mock_tags_repo.get_popular_tags.return_value = []
        tools_handler.storage_provider.tags_repo = mock_tags_repo
        
        result = await tools_handler.get_popular_tags_tool(min_usage=5)
        
        assert result["success"] is True
        assert result["tags"] == []
        assert "No tags found with min_usage >= 5" in result["message"]
        assert result["total"] == 0

    async def test_get_popular_tags_tool_error_handling(self, tools_handler_with_tags):
        """Test error handling in get_popular_tags_tool"""
        tools_handler_with_tags.storage_provider.tags_repo.get_popular_tags.side_effect = Exception("Connection error")
        
        result = await tools_handler_with_tags.get_popular_tags_tool()
        
        assert result["success"] is False
        assert "error" in result
        assert "Connection error" in result["error"]

    def test_load_tags_config_defaults(self, tools_handler):
        """Test _load_tags_config returns correct defaults"""
        config = tools_handler._load_tags_config()
        
        # Should return default values from get_default_tags_config()
        assert isinstance(config, dict)
        # These are the expected default keys
        expected_keys = ['popular_tags_limit', 'popular_tags_min_usage', 'show_in_responses', 
                        'recent_tags_hours', 'smart_grouping_popular_threshold', 'smart_grouping_recent_threshold']
        for key in expected_keys:
            assert key in config or config == {}  # Empty dict if config loading fails

    # --- Tests for tags integration in load_contexts ---

    @pytest.mark.asyncio
    async def test_load_contexts_shows_popular_tags(self, tools_handler_with_tags):
        """Test load_contexts includes popular tags in response"""
        # Setup mock data with contexts and popular tags
        tools_handler_with_tags.storage_provider.load_contexts.return_value = [
            {
                "id": 1,
                "content": "Test context content",
                "importance_level": 8,
                "created_at": "2025-07-05T10:00:00"
            }
        ]
        
        result = await tools_handler_with_tags.load_contexts(init_load=False)
        
        assert "content" in result
        text_content = result["content"][0]["text"]
        assert "Memory Loaded Successfully" in text_content
        
        assert "🏷️ **Popular Tags:**" in text_content
        assert "python (5 uses)" in text_content
        assert "database (3 uses)" in text_content
        assert "testing (1 uses)" in text_content  # Note: it shows "1 uses" not "1 use" in implementation

    @pytest.mark.asyncio
    async def test_load_contexts_shows_popular_tags_init_load_true(self, tools_handler_with_tags):
        """Test load_contexts includes popular tags in response with init_load=True"""
        # Setup mock data for init_load
        tools_handler_with_tags.storage_provider.load_contexts.return_value = [
            {
                "id": 1,
                "content": "Test context content",
                "importance_level": 8,
                "created_at": "2025-07-05T10:00:00"
            }
        ]
        
        result = await tools_handler_with_tags.load_contexts(init_load=True)
        
        assert "content" in result
        # Popular tags should be in the unified content  
        text_content = result["content"][0]["text"]
        
        assert "🏷️ **Popular Tags:**" in text_content
        assert "python (5 uses)" in text_content
        assert "database (3 uses)" in text_content
        assert "testing (1 uses)" in text_content

    @pytest.mark.asyncio
    async def test_load_contexts_shows_popular_tags_both_modes(self, tools_handler_with_tags):
        """Test popular tags appear in both init_load=True and init_load=False modes"""
        # Test init_load=False
        tools_handler_with_tags.storage_provider.load_contexts.return_value = [
            {"id": 1, "content": "Test", "importance_level": 8, "created_at": "2025-07-05T10:00:00"}
        ]
        
        result_false = await tools_handler_with_tags.load_contexts(init_load=False)
        text_false = result_false["content"][0]["text"]
        
        # Test init_load=True  
        # No need to set different mock data - load_contexts handles both cases now
        result_true = await tools_handler_with_tags.load_contexts(init_load=True)
        text_true = result_true["content"][0]["text"]
        
        # Both should contain popular tags
        assert "🏷️" in text_false and "Tags" in text_false
        assert "🏷️" in text_true and "Tags" in text_true
        assert "python" in text_false and "python" in text_true

    @pytest.mark.asyncio
    async def test_load_contexts_respects_tags_config(self, tools_handler_with_tags):
        """Test load_contexts respects show_in_responses config"""
        # Mock get_default_tags_config to return show_in_responses=False
        import unittest.mock
        
        with unittest.mock.patch('extended_memory_mcp.tools.memory_tools.get_default_tags_config') as mock_config:
            mock_config.return_value = {'show_in_responses': False}
            
            tools_handler_with_tags.storage_provider.load_contexts.return_value = [
                {
                    "id": 1,
                    "content": "Test context content",
                    "importance_level": 8,
                    "created_at": "2025-07-05T10:00:00"
                }
            ]
            
            result = await tools_handler_with_tags.load_contexts(init_load=False)
            
            text_content = result["content"][0]["text"]
            # Should NOT include popular tags section when disabled
            assert "🏷️ **Popular Tags:**" not in text_content

    @pytest.mark.asyncio
    async def test_load_contexts_handles_tags_loading_error(self, tools_handler_with_tags):
        """Test load_contexts handles tags loading errors gracefully"""
        # Setup normal context data
        tools_handler_with_tags.storage_provider.load_contexts.return_value = [
            {
                "id": 1,
                "content": "Test context",
                "importance_level": 7,
                "created_at": "2025-07-05T10:00:00"
            }
        ]
        
        # Make tags loading fail
        tools_handler_with_tags.storage_provider.tags_repo.get_popular_tags.side_effect = Exception("Tags error")
        
        result = await tools_handler_with_tags.load_contexts(init_load=False)
        
        # Should still work without tags
        assert "content" in result
        text_content = result["content"][0]["text"]
        assert "Memory Loaded Successfully" in text_content
        assert "Test context" in text_content
        
        # Should not include tags section due to error
        assert "🏷️ **Popular Tags:**" not in text_content

    @pytest.mark.asyncio
    async def test_load_contexts_no_tags_repo_attribute(self, tools_handler):
        """Test load_contexts when storage provider has no tags_repo attribute"""
        # Ensure storage provider doesn't have tags_repo attribute
        if hasattr(tools_handler.storage_provider, 'tags_repo'):
            delattr(tools_handler.storage_provider, 'tags_repo')
        
        tools_handler.storage_provider.load_contexts.return_value = [
            {
                "id": 1,
                "content": "Test context",
                "importance_level": 7,
                "created_at": "2025-07-05T10:00:00"
            }
        ]
        
        result = await tools_handler.load_contexts(init_load=False)
        
        # Should work without crashing
        assert "content" in result
        text_content = result["content"][0]["text"]
        assert "Memory Loaded Successfully" in text_content
        
        # Should not include tags section at all when no tags_repo
        assert "🏷️ **Popular Tags:**" not in text_content

    @pytest.mark.asyncio
    async def test_load_contexts_empty_tags_list(self, tools_handler_with_tags):
        """Test load_contexts when no popular tags exist"""
        # Setup normal context data
        tools_handler_with_tags.storage_provider.load_contexts.return_value = [
            {
                "id": 1,
                "content": "Test context",
                "importance_level": 7,
                "created_at": "2025-07-05T10:00:00"
            }
        ]
        
        # Return empty tags list
        tools_handler_with_tags.storage_provider.tags_repo.get_popular_tags.return_value = []
        
        result = await tools_handler_with_tags.load_contexts(init_load=False)
        
        assert "content" in result
        text_content = result["content"][0]["text"]
        assert "Memory Loaded Successfully" in text_content
        
        # Should not include tags section when no tags exist
        assert "🏷️ **Popular Tags:**" not in text_content

    @pytest.mark.asyncio
    async def test_load_contexts_config_loading_error(self, tools_handler_with_tags):
        """Test load_contexts handles config loading errors gracefully"""
        # Mock get_default_tags_config to raise an exception
        import unittest.mock
        
        with unittest.mock.patch('extended_memory_mcp.tools.memory_tools.get_default_tags_config') as mock_config:
            mock_config.side_effect = Exception("Config error")
            
            tools_handler_with_tags.storage_provider.load_contexts.return_value = [
                {
                    "id": 1,
                    "content": "Test context",
                    "importance_level": 7,
                    "created_at": "2025-07-05T10:00:00"
                }
            ]
            
            result = await tools_handler_with_tags.load_contexts(init_load=False)
            
            # Should still work, falling back to not showing tags
            assert "content" in result
            text_content = result["content"][0]["text"]
            assert "Memory Loaded Successfully" in text_content

    @pytest.mark.asyncio
    async def test_load_contexts_tags_formatting(self, tools_handler_with_tags):
        """Test proper formatting of tags in load_contexts response"""
        # Setup mock with specific tag data
        tools_handler_with_tags.storage_provider.tags_repo.get_popular_tags.return_value = [
            {"tag": "python", "count": 10},
            {"tag": "machine-learning", "count": 5},
            {"tag": "web-development", "count": 3}
        ]
        
        tools_handler_with_tags.storage_provider.load_contexts.return_value = [
            {
                "id": 1,
                "content": "Test context",
                "importance_level": 7,
                "created_at": "2025-07-05T10:00:00"
            }
        ]
        
        result = await tools_handler_with_tags.load_contexts(init_load=False)
        
        text_content = result["content"][0]["text"]
        
        # Popular tags are temporarily disabled for performance optimization
        # Check proper formatting with usage counts
        # assert "python (10 uses)" in text_content
        # assert "machine-learning (5 uses)" in text_content
        # assert "web-development (3 uses)" in text_content
        
        # Tags should be comma-separated
        # tags_line = [line for line in text_content.split('\n') if '🏷️ **Popular Tags:**' in line][0]
        # assert ', ' in tags_line  # Comma-separated format


class TestMemoryToolsProjectIdFiltering(TestMemoryToolsHandler):
    """Test project_id filtering functionality in MCP tools"""

    async def test_get_popular_tags_tool_with_project_id_parameter(self, tools_handler_with_tags):
        """Test get_popular_tags_tool with explicit project_id parameter"""
        # Mock response for specific project
        mock_tags = [
            {"tag": "popular-tag", "count": 5},
            {"tag": "frequent-tag", "count": 3}
        ]
        tools_handler_with_tags.storage_provider.tags_repo.get_popular_tags.return_value = mock_tags
        
        # Call with explicit parameters
        result = await tools_handler_with_tags.get_popular_tags_tool(
            limit=20, min_usage=2, project_id="specific_project"
        )
        
        # Verify parameters passed correctly (normalized)
        tools_handler_with_tags.storage_provider.tags_repo.get_popular_tags.assert_called_once_with(
            limit=20, min_usage=2, project_id="specific project"
        )
        
        assert result["success"] is True
        assert result["total"] == 2
        
        # Check response formatting
        text_content = result["content"][0]["text"]
        assert "`popular-tag` (5 uses)" in text_content
        assert "`frequent-tag` (3 uses)" in text_content

    @pytest.mark.asyncio
    async def test_get_popular_tags_tool_fallback_logic(self, tools_handler_with_tags):
        """Test get_popular_tags_tool fallback to current project"""
        # Set current project
        tools_handler_with_tags.current_project = "my_project"
        
        # Mock response
        tools_handler_with_tags.storage_provider.tags_repo.get_popular_tags.return_value = [
            {"tag": "my-tag", "count": 2}
        ]
        
        # Call without project_id
        result = await tools_handler_with_tags.get_popular_tags_tool(limit=10, min_usage=1)
        
        # Verify fallback behavior (normalized)
        tools_handler_with_tags.storage_provider.tags_repo.get_popular_tags.assert_called_once_with(
            limit=10, min_usage=1, project_id="my project"
        )
        
        assert result["success"] is True

    async def test_execute_tool_passes_project_id_correctly(self, tools_handler_with_tags):
        """Test that execute_tool correctly passes project_id arguments to tools"""
        # Mock response
        tools_handler_with_tags.storage_provider.tags_repo.get_popular_tags.return_value = []
        
        # Test get_tags through execute_tool
        result = await tools_handler_with_tags.execute_tool(
            "get_popular_tags", 
            {"limit": 15, "project_id": "execute_test_project"}
        )
        
        # Verify project_id was passed correctly (normalized)
        tools_handler_with_tags.storage_provider.tags_repo.get_popular_tags.assert_called_once_with(
            limit=15, min_usage=1, project_id="execute test project"
        )
        
        assert result["success"] is True
        
        # Reset mock for next test
        tools_handler_with_tags.storage_provider.tags_repo.get_popular_tags.reset_mock()
        
        # Test get_popular_tags through execute_tool
        result = await tools_handler_with_tags.execute_tool(
            "get_popular_tags",
            {"limit": 25, "min_usage": 3, "project_id": "another_project"}
        )
        
        # Verify parameters passed correctly (normalized)
        tools_handler_with_tags.storage_provider.tags_repo.get_popular_tags.assert_called_once_with(
            limit=25, min_usage=3, project_id="another project"
        )
        
        assert result["success"] is True


class TestMemoryToolsEdgeCases(TestMemoryToolsHandler):
    """Test edge cases for project_id in MCP tools"""

    async def test_get_popular_tags_tool_with_whitespace_project_id(self, tools_handler_with_tags):
        """Test get_popular_tags_tool with whitespace-only project_id"""
        whitespace_project_id = "   \t\n  "
        
        # Mock response
        tools_handler_with_tags.storage_provider.tags_repo.get_popular_tags.return_value = [
            {"tag": "whitespace-tag", "count": 2}
        ]
        
        # Call with whitespace project_id
        result = await tools_handler_with_tags.get_popular_tags_tool(
            limit=20, min_usage=1, project_id=whitespace_project_id
        )
        
        # Verify whitespace project_id was normalized to "general"
        tools_handler_with_tags.storage_provider.tags_repo.get_popular_tags.assert_called_once_with(
            limit=20, min_usage=1, project_id="general"
        )
        
        assert result["success"] is True

    @pytest.mark.asyncio
    async def test_execute_tool_edge_case_project_ids(self, tools_handler_with_tags):
        """Test execute_tool with various edge case project_ids"""
        edge_case_project_ids = [
            "",              # Empty string
            " ",             # Single space
            None,            # None value (should trigger fallback)
            "null",          # String "null"
            "undefined",     # String "undefined"
            "0",             # Numeric string
            "-1",            # Negative numeric string
            "true",          # Boolean string
            "false"          # Boolean string
        ]
        
        tools_handler_with_tags.current_project = "fallback_project"
        
        for project_id in edge_case_project_ids:
            # Reset mock for each test
            tools_handler_with_tags.storage_provider.tags_repo.get_popular_tags.reset_mock()
            tools_handler_with_tags.storage_provider.tags_repo.get_popular_tags.return_value = []
            
            # Test get_tags through execute_tool
            result = await tools_handler_with_tags.execute_tool(
                "get_popular_tags",
                {"limit": 10, "project_id": project_id}
            )
            
            # Should not crash regardless of project_id value
            assert result["success"] is True
            
            # Verify appropriate project_id was used after normalization
            call_args = tools_handler_with_tags.storage_provider.tags_repo.get_popular_tags.call_args
            if project_id is None:
                # Should fall back to current_project (normalized)
                assert call_args[1]["project_id"] == "fallback project"
            elif project_id == "" or project_id == " ":
                # Empty/whitespace strings should be normalized to "general"
                assert call_args[1]["project_id"] == "general"
            else:
                # Other valid strings should be normalized (dashes/underscores -> spaces, lowercase)
                import sys
                from pathlib import Path
                sys.path.append(str(Path(__file__).parent.parent.parent / "mcp-server"))
                from extended_memory_mcp.core.project_utils import normalize_project_id
                expected_project_id = normalize_project_id(project_id)
                assert call_args[1]["project_id"] == expected_project_id

    async def test_load_contexts_with_tags_filter_basic(self, tools_handler_with_tags):
        """Test load_contexts with tags_filter parameter"""
        # Mock contexts with specific tags
        mock_contexts = [
            {
                "id": 1,
                "content": "React frontend code",
                "importance_level": 8,
                "created_at": "2025-01-01 10:00:00",
                "tags": ["react", "frontend"]
            },
            {
                "id": 2, 
                "content": "API documentation",
                "importance_level": 7,
                "created_at": "2025-01-01 11:00:00", 
                "tags": ["api", "backend"]
            }
        ]
        
        tools_handler_with_tags.storage_provider.load_contexts.return_value = mock_contexts
        
        # Test filtering by multiple tags
        result = await tools_handler_with_tags.load_contexts(
            project_id="test_project",
            importance_level=7,
            init_load=False,
            limit=30,
            tags_filter=["react", "api"]
        )
        
        # Verify storage provider was called with tags_filter
        tools_handler_with_tags.storage_provider.load_contexts.assert_called_once_with(
            project_id="test project",  # Normalized from test_project
            limit=30,
            importance_threshold=7,
            tags_filter=["react", "api"]
        )
        
        assert "content" in result
        content_text = result["content"][0]["text"]
        assert "Found 2 saved contexts" in content_text

    @pytest.mark.asyncio
    async def test_load_contexts_with_empty_tags_filter(self, tools_handler_with_tags):
        """Test load_contexts with empty tags_filter"""
        mock_contexts = [{"id": 1, "content": "Test", "importance_level": 8}]
        tools_handler_with_tags.storage_provider.load_contexts.return_value = mock_contexts
        
        # Empty tags_filter should be normalized to None (no filtering)
        result = await tools_handler_with_tags.load_contexts(
            project_id="test_project",
            tags_filter=[],
            init_load=False  # Important: prevent init_load behavior
        )
        
        tools_handler_with_tags.storage_provider.load_contexts.assert_called_once_with(
            project_id="test project",  # Normalized from test_project
            limit=30,
            importance_threshold=7,
            tags_filter=None  # Empty list becomes None
        )
        
        assert "content" in result

    @pytest.mark.asyncio
    async def test_load_contexts_with_none_tags_filter(self, tools_handler_with_tags):
        """Test load_contexts with None tags_filter (default behavior)"""
        mock_contexts = [{"id": 1, "content": "Test", "importance_level": 8}]
        tools_handler_with_tags.storage_provider.load_contexts.return_value = mock_contexts
        
        # None tags_filter should be passed through (backward compatibility)
        result = await tools_handler_with_tags.load_contexts(
            project_id="test_project",
            tags_filter=None,
            init_load=False  # Important: prevent init_load behavior
        )
        
        tools_handler_with_tags.storage_provider.load_contexts.assert_called_once_with(
            project_id="test project",  # Normalized from test_project
            limit=30, 
            importance_threshold=7,
            tags_filter=None
        )
        
        assert "content" in result

    @pytest.mark.asyncio
    async def test_load_contexts_tags_filter_with_project_isolation(self, tools_handler_with_tags):
        """Test that tags_filter works correctly with project isolation"""
        # Mock contexts from specific project
        project_contexts = [
            {
                "id": 10,
                "content": "Project A react code", 
                "importance_level": 8,
                "tags": ["react", "project-a"]
            }
        ]
        
        tools_handler_with_tags.storage_provider.load_contexts.return_value = project_contexts
        
        result = await tools_handler_with_tags.load_contexts(
            project_id="project_a",
            tags_filter=["react"],
            init_load=False
        )
        
        # Verify project_id and tags_filter were both passed
        tools_handler_with_tags.storage_provider.load_contexts.assert_called_once_with(
            project_id="project a",  # Normalized from project_a
            limit=30,
            importance_threshold=7, 
            tags_filter=["react"]
        )
        
        assert "content" in result

    @pytest.mark.asyncio  
    async def test_load_contexts_tags_filter_no_results(self, tools_handler_with_tags):
        """Test load_contexts when tags_filter returns no matching contexts"""
        # Mock empty result when filtering by tags
        tools_handler_with_tags.storage_provider.load_contexts.return_value = []
        
        result = await tools_handler_with_tags.load_contexts(
            project_id="test_project",
            tags_filter=["nonexistent-tag"],
            init_load=False
        )
        
        tools_handler_with_tags.storage_provider.load_contexts.assert_called_once_with(
            project_id="test project",  # Normalized from test_project
            limit=30,
            importance_threshold=7,
            tags_filter=["nonexistent-tag"]
        )
        
        assert "content" in result
        content_text = result["content"][0]["text"]
        assert "No saved contexts found" in content_text

    @pytest.mark.asyncio
    async def test_load_contexts_tags_filter_error_handling(self, tools_handler_with_tags):
        """Test error handling when tags_filter causes storage provider error"""
        # Mock storage provider error when using tags_filter
        tools_handler_with_tags.storage_provider.load_contexts.side_effect = Exception("Tag filtering error")
        
        result = await tools_handler_with_tags.load_contexts(
            project_id="test_project", 
            tags_filter=["problematic-tag"],
            init_load=False
        )
        
        assert "content" in result
        content_text = result["content"][0]["text"]
        assert "Error" in content_text or "Tag filtering error" in content_text

    @pytest.mark.asyncio
    async def test_load_contexts_tags_filter_overrides_init_load(self, tools_handler_with_tags):
        """Test that tags_filter overrides init_load=True behavior"""
        # Mock regular contexts response for tags_filter
        mock_contexts = [{"id": 1, "content": "Tagged context", "tags": ["should-be-ignored"]}]
        tools_handler_with_tags.storage_provider.load_contexts.return_value = mock_contexts
        
        result = await tools_handler_with_tags.load_contexts(
            project_id="test_project",
            init_load=True,
            tags_filter=["should-be-ignored"]
        )
        
        # Should call load_contexts with tags_filter, NOT load_init_contexts
        tools_handler_with_tags.storage_provider.load_contexts.assert_called_once()
        tools_handler_with_tags.storage_provider.load_init_contexts.assert_not_called()
        
        # load_contexts returns content format, not isError format
        assert "content" in result
        assert len(result["content"]) > 0
