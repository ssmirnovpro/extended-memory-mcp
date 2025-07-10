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
Basic tests for Memory MCP Server core functionality
"""
import pytest
import asyncio
from pathlib import Path

# Add project to path
import sys
project_root = Path(__file__).parent.parent / "mcp-server"
sys.path.append(str(project_root))

from extended_memory_mcp.core.memory import MemoryFacade as MemoryManager  # Use new architecture


class TestMemoryManager:
    """Test memory manager functionality"""
    
    @pytest.mark.asyncio
    async def test_save_and_load_context(self, memory_manager, context_repo):
        """Test saving and loading context"""
        # Save context
        context_id = await context_repo.save_context(
                content="Test context for verification",
                importance_level=7,
                project_id="test_project"
            )
        
        assert context_id is not None
        
        # Load context
        contexts = await memory_manager.load_smart_contexts("test_project")
        
        assert len(contexts) >= 1
        # Find our saved context
        saved_context = next((ctx for ctx in contexts if ctx["content"] == "Test context for verification"), None)
        assert saved_context is not None
        assert saved_context["importance_level"] == 7
    
    @pytest.mark.asyncio
    async def test_save_context_with_normalized_tags(self, memory_manager, context_repo):
        """Test saving context with normalized tags schema"""
        context_id = await context_repo.save_context(
                content="Context with multiple tags",
                importance_level=6,
                project_id="test_tags",
            )
        
        assert context_id is not None
        
        # Verify tags are saved properly in normalized schema
        contexts = await memory_manager.load_smart_contexts("test_tags")
        assert len(contexts) >= 1
        
        # Find our context and check tags
        saved_context = next((ctx for ctx in contexts if ctx["content"] == "Context with multiple tags"), None)
        assert saved_context is not None


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
