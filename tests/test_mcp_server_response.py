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
Critical Tests for MCP Server Response Format
Tests that ensure server returns actual content, not just summaries
"""

import pytest
import pytest_asyncio
import asyncio
import tempfile
import json
import os
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

# Add project path
import sys
project_root = Path(__file__).parent.parent / "mcp-server"
sys.path.append(str(project_root))

from extended_memory_mcp.server import MemoryMCPServer
from extended_memory_mcp.core.storage.storage_factory import StorageFactory


class TestMCPServerResponse:
    """Critical tests for MCP server response formatting"""
    
    @pytest_asyncio.fixture
    async def mock_server(self):
        """Create MCP server with temporary SQLite database for testing"""
        with tempfile.TemporaryDirectory() as temp_dir:
            # Create temporary SQLite database
            db_path = Path(temp_dir) / "test_memory.db"
            test_connection_string = f"sqlite:///{db_path}"
            
            # Create temporary instruction file
            instruction_path = Path(temp_dir) / "test_instruction.md"
            with open(instruction_path, 'w') as f:
                f.write("# Session Initialization\n\nThis is a test custom instruction for the tests.")
            
            # Mock the connection string and custom instruction path for this test
            env_vars = {
                'STORAGE_CONNECTION_STRING': test_connection_string,
                'CUSTOM_INSTRUCTION_PATH': str(instruction_path)
            }
            with patch.dict(os.environ, env_vars):
                # Create and initialize server with test database
                server = MemoryMCPServer()
                await server.initialize()
                
                # Add test project data
                project_id = await server.storage_provider.save_context(
                    content="Memory MCP project - revolutionary system for Claude context preservation.",
                    importance_level=9,
                    project_id="memory mcp"  # Use normalized form directly
                )
                
                yield server
    
    @pytest.mark.asyncio
    async def test_load_contexts_init_returns_actual_content(self, mock_server, context_repo):
        """CRITICAL: Test that init_load returns actual context content, not just summary"""
        
        # Call load_contexts through MCP tools handler with init_load=True
        response = await mock_server.tools_handler.load_contexts(
            project_id="memory_mcp",  # This will be normalized to "memory mcp"
            init_load=True,
            limit=10
        )
        
        # Verify response structure
        assert "content" in response
        assert isinstance(response["content"], list)
        assert len(response["content"]) == 1  # unified response after architecture unification
        
        # Debug: print actual response structure for analysis
        print("\n=== DEBUG: Response content ===")
        for i, part in enumerate(response["content"]):
            text = part.get('text', '')
            print(f"Part {i} (first 500 chars): {text[:500]}")
        print("=== END DEBUG ===\n")
        
        # Find the unified content (now everything is in one section)
        text_content = response["content"][0].get("text", "")
        
        # Debug output
        print(f"\n=== DEBUG: Unified content (first 500 chars): {text_content[:500]} ===\n")
        
        # CRITICAL CHECK: Must contain actual content, not just summary
        assert "Memory MCP project - revolutionary system" in text_content, \
            "Actual context content missing from response!"
        
        # Verify we have detailed context information
        assert "📝" in text_content, \
            "Response missing detailed context content formatting!"
    
    @pytest.mark.asyncio
    async def test_init_load_false_returns_content(self, mock_server, context_repo):
        """Test that regular load also returns actual content"""
        
        # Save some test context data
        context_id = await context_repo.save_context(
            content="Memory MCP project - revolutionary system for session continuity",
            importance_level=8,
            project_id="memory_mcp"
        )
        
        # Add tags
        if context_id:
            await mock_server.storage_provider.tags_repo.save_context_tags(context_id, ["project", "architecture"])
        
        response = await mock_server.tools_handler.load_contexts(
            project_id="memory_mcp",
            limit=10
        )
        
        # Should still get content, not just summary
        assert "content" in response
        content_text = response["content"][0]["text"]
        
        # Must contain instruction content (always present)
        assert "Session Initialization" in content_text, \
            "Missing Session Initialization content!"
    
    @pytest.mark.asyncio
    async def test_context_type_filtering_returns_content(self, mock_server, context_repo):
        """Test that filtered loading returns actual content"""
        
        # Save some test context data
        context_id = await context_repo.save_context(
            content="Technical details about MCP implementation and architecture",
            importance_level=7,
            project_id="memory_mcp"
        )
        
        # Add tags
        if context_id:
            await mock_server.storage_provider.tags_repo.save_context_tags(context_id, ["technical", "mcp", "architecture"])
        
        response = await mock_server.tools_handler.load_contexts(
            project_id="memory_mcp",
            limit=10
        )
        
        # Should get filtered content
        content_text = response["content"][0]["text"]
        
        # Must contain init instruction (always present)
        assert "Session Initialization" in content_text, \
            "Filtered load missing actual content!"
    
    @pytest.mark.asyncio
    async def test_empty_contexts_handling(self, mock_server, context_repo):
        """Test handling when no contexts found"""
        
        response = await mock_server.tools_handler.load_contexts(
            project_id="nonexistent_project",
            limit=10
        )
        
        # Should handle gracefully
        assert "content" in response
        content_text = response["content"][0]["text"]
        
        # Should contain empty memory message for nonexistent project
        assert "No saved contexts found" in content_text, \
            "Empty project response missing proper empty message!"

    @pytest.mark.asyncio
    async def test_response_format_consistency(self, mock_server, context_repo):
        """Test that response format is consistent with Claude Desktop expectations"""
        
        response = await mock_server.tools_handler.load_contexts(
        )
        
        # Check MCP response format
        assert isinstance(response, dict)
        assert "content" in response
        # Note: isError might not always be present, depends on implementation
        
        # Check content structure
        for content_part in response["content"]:
            assert "type" in content_part
            assert "text" in content_part
            assert content_part["type"] == "text"
            assert isinstance(content_part["text"], str)
            assert len(content_part["text"]) > 0


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
