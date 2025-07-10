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
Test for list_all_projects functionality
"""
import pytest
import asyncio
import logging
from pathlib import Path
from unittest.mock import AsyncMock

# Add project to path
import sys
project_root = Path(__file__).parent.parent / "mcp-server"
sys.path.append(str(project_root))

from extended_memory_mcp.tools.memory_tools import MemoryToolsHandler
from extended_memory_mcp.formatters.summary_formatter import ContextSummaryFormatter


@pytest.fixture
def mock_storage_provider():
    """Create mock storage provider for fast testing"""
    mock = AsyncMock()
    mock.save_context.return_value = "123"
    mock.list_all_projects_global.return_value = [
        {"id": "test_project_a", "name": "test_project_a", "context_count": 1},
        {"id": "test_project_b", "name": "test_project_b", "context_count": 1},
        {"id": "comparison_test_project", "name": "comparison_test_project", "context_count": 1}
    ]
    return mock


@pytest.fixture
def summary_formatter():
    """Create summary formatter"""
    return ContextSummaryFormatter()


@pytest.fixture
def mock_logger():
    """Create mock logger"""
    return logging.getLogger("test")


@pytest.fixture
def tools_handler(mock_storage_provider, summary_formatter, mock_logger):
    """Create MemoryToolsHandler with mocked storage for fast testing"""
    return MemoryToolsHandler(mock_storage_provider, summary_formatter, mock_logger)


@pytest.mark.asyncio
async def test_list_all_projects_tool_basic(tools_handler):
    """Test list_all_projects tool returns correct format"""
    
    # Create test projects by saving contexts (mocked)
    await tools_handler.save_context(
        content="Test context in project A",
        importance_level=7,
        project_id="test_project_a"
    )
    
    await tools_handler.save_context(
        content="Test context in project B", 
        importance_level=7,
        project_id="test_project_b"
    )
    
    # Test the new tool
    result = await tools_handler.list_all_projects_global()
    
    # Debug: print what we got
    print(f"DEBUG: result = {result}")
    
    # Check result format - list_all_projects returns content format, not success format
    assert isinstance(result, dict)
    assert "content" in result
    assert len(result["content"]) > 0
    assert "type" in result["content"][0]
    assert result["content"][0]["type"] == "text"
    
    # Check that response contains our test projects
    response_text = result["content"][0]["text"]
    assert "test_project_a" in response_text
    assert "test_project_b" in response_text

@pytest.mark.asyncio  
async def test_list_all_projects_comprehensive(tools_handler):
    """Test that list_all_projects_global works comprehensively"""
    
    # Create a test project
    await tools_handler.save_context(
        content="Test context for comprehensive test",
        importance_level=7,
        project_id="comprehensive_test_project"
    )
    
    # Get results
    all_projects_result = await tools_handler.list_all_projects_global()
    
    # Should succeed
    assert "content" in all_projects_result
    content_text = all_projects_result["content"][0]["text"]
    assert "All Projects" in content_text


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
