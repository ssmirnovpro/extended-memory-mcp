#!/usr/bin/env python3

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


# Extended Memory MCP Server
# Copyright (C) 2025 Sergey Smirnov
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as published
# by the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
# GNU Affero General Public License for more details.
#
# You should have received a copy of the GNU Affero General Public License
# along with this program. If not, see <https://www.gnu.org/licenses/>.

"""
Tests for MCP Protocol Handler

Tests the MCP protocol handling logic separated from main server.
"""

import json
import logging
import pytest
from unittest.mock import AsyncMock, MagicMock

from extended_memory_mcp.protocol.mcp_protocol_handler import MCPProtocolHandler, create_mcp_protocol_handler


class TestMCPProtocolHandler:
    """Test suite for MCPProtocolHandler"""
    
    @pytest.fixture
    def logger(self):
        """Create mock logger"""
        logger = MagicMock(spec=logging.Logger)
        logger.trace = MagicMock()
        return logger
    
    @pytest.fixture
    def protocol_handler(self, logger):
        """Create protocol handler instance"""
        return MCPProtocolHandler(logger)
    
    @pytest.fixture
    def mock_tools_handler(self):
        """Create mock tools handler"""
        tools_handler = AsyncMock()
        tools_handler.execute_tool.return_value = {"content": [{"type": "text", "text": "Tool executed"}]}
        return tools_handler
    
    @pytest.fixture
    def mock_server(self):
        """Create mock server instance"""
        server = AsyncMock()
        server.generate_startup_context.return_value = {
            "user_name": "User",
            "message": "Test startup context"
        }
        return server
    
    async def test_handle_initialize(self, protocol_handler):
        """Test initialize request handling"""
        result = await protocol_handler.handle_request(
            method="initialize",
            params={},
            tools_handler=None,
            server=None
        )
        
        assert result["protocolVersion"] == "2024-11-05"
        assert "capabilities" in result
        assert "serverInfo" in result
        assert result["serverInfo"]["name"] == "memory-server"
    
    async def test_handle_notifications_initialized(self, protocol_handler):
        """Test notifications/initialized handling (should return None)"""
        result = await protocol_handler.handle_request(
            method="notifications/initialized",
            params={},
            tools_handler=None,
            server=None
        )
        
        assert result is None
    
    async def test_handle_prompts_get_memory_instructions(self, protocol_handler):
        """Test prompts/get for memory_instructions"""
        result = await protocol_handler.handle_request(
            method="prompts/get",
            params={"name": "memory_instructions"},
            tools_handler=None,
            server=None
        )
        
        assert "description" in result
        assert "messages" in result
        assert len(result["messages"]) > 0
    
    async def test_handle_prompts_get_unknown(self, protocol_handler):
        """Test prompts/get for unknown prompt"""
        with pytest.raises(Exception, match="Unknown prompt"):
            await protocol_handler.handle_request(
                method="prompts/get",
                params={"name": "unknown_prompt"},
                tools_handler=None,
                server=None
            )
    
    async def test_handle_resources_read_startup_context(self, protocol_handler, mock_server):
        """Test resources/read for startup context"""
        result = await protocol_handler.handle_request(
            method="resources/read",
            params={"uri": "memory://startup-context"},
            tools_handler=None,
            server=mock_server
        )
        
        assert "contents" in result
        assert len(result["contents"]) == 1
        content = result["contents"][0]
        assert content["uri"] == "memory://startup-context"
        assert content["mimeType"] == "application/json"
        
        # Verify startup context was called
        mock_server.generate_startup_context.assert_called_once()
    
    async def test_handle_resources_read_unknown_uri(self, protocol_handler, mock_server):
        """Test resources/read for unknown URI"""
        with pytest.raises(Exception, match="Unknown resource URI"):
            await protocol_handler.handle_request(
                method="resources/read",
                params={"uri": "unknown://uri"},
                tools_handler=None,
                server=mock_server
            )
    
    async def test_handle_resources_list(self, protocol_handler):
        """Test resources/list"""
        result = await protocol_handler.handle_request(
            method="resources/list",
            params={},
            tools_handler=None,
            server=None
        )
        
        assert "resources" in result
        assert len(result["resources"]) > 0
        
        # Check startup context resource is included
        startup_resource = next(
            (r for r in result["resources"] if r["uri"] == "memory://startup-context"),
            None
        )
        assert startup_resource is not None
    
    async def test_handle_prompts_list(self, protocol_handler):
        """Test prompts/list"""
        result = await protocol_handler.handle_request(
            method="prompts/list",
            params={},
            tools_handler=None,
            server=None
        )
        
        assert "prompts" in result
        assert len(result["prompts"]) > 0
        
        # Check memory_instructions prompt is included
        memory_prompt = next(
            (p for p in result["prompts"] if p["name"] == "memory_instructions"),
            None
        )
        assert memory_prompt is not None
    
    async def test_handle_tools_list(self, protocol_handler):
        """Test tools/list"""
        result = await protocol_handler.handle_request(
            method="tools/list",
            params={},
            tools_handler=None,
            server=None
        )
        
        assert "tools" in result
        tools = result["tools"]
        assert len(tools) == 5  # save_context, load_contexts, forget_context, list_projects, get_popular_tags
        
        # Check that we have expected tools
        tool_names = [tool["name"] for tool in tools]
        expected_tools = ["save_context", "load_contexts", "forget_context", "list_all_projects", "get_popular_tags"]
        assert set(tool_names) == set(expected_tools), f"Expected {expected_tools}, got {tool_names}"
    
    async def test_handle_tools_call(self, protocol_handler, mock_tools_handler):
        """Test tools/call delegation"""
        result = await protocol_handler.handle_request(
            method="tools/call",
            params={"name": "save_context", "arguments": {"content": "Test content"}},
            tools_handler=mock_tools_handler,
            server=None
        )
        
        # Verify tools handler was called
        mock_tools_handler.execute_tool.assert_called_once_with(
            "save_context", 
            {"content": "Test content"}
        )
        
        # Verify result passed through
        assert result == {"content": [{"type": "text", "text": "Tool executed"}]}
    
    async def test_handle_unknown_method(self, protocol_handler):
        """Test handling of unknown method"""
        with pytest.raises(Exception, match="Unknown method"):
            await protocol_handler.handle_request(
                method="unknown/method",
                params={},
                tools_handler=None,
                server=None
            )
    
    async def test_logging_integration(self, protocol_handler, logger):
        """Test that logging functions are called"""
        # Successful request
        await protocol_handler.handle_request(
            method="initialize",
            params={},
            tools_handler=None,
            server=None,
            request_id="test-123"
        )
        
        # Verify trace logging was called (if logger supports it)
        assert logger.trace.call_count >= 2  # request + response
    
    async def test_error_handling_and_logging(self, protocol_handler, logger, mock_tools_handler):
        """Test error handling and logging"""
        # Make tools handler raise an exception
        mock_tools_handler.execute_tool.side_effect = RuntimeError("Test error")
        
        with pytest.raises(RuntimeError, match="Test error"):
            await protocol_handler.handle_request(
                method="tools/call",
                params={"name": "save_context", "arguments": {"content": "Test"}},
                tools_handler=mock_tools_handler,
                server=None,
                request_id="error-test"
            )
        
        # Verify error logging occurred
        assert logger.trace.call_count >= 1


class TestProtocolHandlerFactory:
    """Test the factory function"""
    
    def test_create_mcp_protocol_handler(self):
        """Test factory function creates proper instance"""
        logger = MagicMock(spec=logging.Logger)
        handler = create_mcp_protocol_handler(logger)
        
        assert isinstance(handler, MCPProtocolHandler)
        assert handler.logger is logger