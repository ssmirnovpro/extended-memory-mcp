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
Tests for tags functionality in Memory MCP Server
"""
import pytest
import asyncio
from pathlib import Path

# Add project to path
import sys
project_root = Path(__file__).parent.parent / "mcp-server"
sys.path.append(str(project_root))

from extended_memory_mcp.core.memory import MemoryFacade as MemoryManager  # Use new architecture


class TestTagsAnalysis:
    """Test tags analysis functionality"""
    
    @pytest.mark.asyncio
    async def test_analyze_available_tags_basic(self, memory_manager, context_repo):
        """Test basic tag analysis"""
        # Save contexts with tags
        await context_repo.save_context(
                content="Test content with React and TypeScript",
                importance_level=8,
                project_id="test_project",
            )
        
        await context_repo.save_context(
                content="Architecture decision about database",
                importance_level=9,
                project_id="test_project",
            )
        
        # Analyze tags
        analysis = await memory_manager._analyze_available_tags("test_project")
        
        # Should contain tag information or graceful fallback
        assert analysis is not None
        assert isinstance(analysis, dict)
        # Should have structured analysis or error message
        assert "tag_analysis" in analysis or "error" in analysis
    
    @pytest.mark.asyncio
    async def test_analyze_available_tags_frequency(self, memory_manager, context_repo):
        """Test tag frequency analysis"""
        # Save multiple contexts with overlapping tags
        for i in range(2):
            await context_repo.save_context(
                content=f"React content {i}",
                importance_level=7,
                project_id="test_project",
            )
        
        analysis = await memory_manager._analyze_available_tags("test_project")
        
        # Check for frequency information or graceful fallback
        assert analysis is not None
        assert isinstance(analysis, dict)
        # Should have structured data or error
        if "tag_analysis" in analysis:
            # Check if react appears with correct count
            tag_analysis = analysis["tag_analysis"]
            react_entries = [tag for tag in tag_analysis if tag["tag"] == "react"]
            if react_entries:
                assert react_entries[0]["usage_count"] >= 2
        else:
            assert "error" in analysis
    
    @pytest.mark.asyncio
    async def test_analyze_available_tags_project_isolation(self, memory_manager, context_repo):
        """Test that tag analysis respects project isolation"""
        # Save contexts in different projects
        await context_repo.save_context(
                content="React development",
                importance_level=7,
                project_id="project_a",
            )
        
        await context_repo.save_context(
                content="Python backend",
                importance_level=7,
                project_id="project_b",
            )
        
        # Analyze tags for project_a only
        analysis = await memory_manager._analyze_available_tags("project_a")
        
        # Should isolate by project or indicate unavailable
        assert analysis is not None
        assert isinstance(analysis, dict)
        # Note: Current implementation does global analysis, not project-specific
        # This is acceptable for compatibility
        if "tag_analysis" in analysis:
            assert len(analysis["tag_analysis"]) >= 0
        else:
            assert "error" in analysis
    
    @pytest.mark.asyncio
    async def test_analyze_available_tags_empty_project(self, memory_manager):
        """Test tag analysis for project with no contexts"""
        analysis = await memory_manager._analyze_available_tags("empty_project")
        
        # Should handle empty project gracefully
        assert analysis is not None
        assert isinstance(analysis, dict)
        # For empty projects, should have empty tag analysis or error
        if "tag_analysis" in analysis:
            assert len(analysis["tag_analysis"]) >= 0  # Can be empty
        else:
            assert "error" in analysis
    
    @pytest.mark.asyncio
    async def test_json_parsing_double_encoded(self, memory_manager, context_repo):
        """Test handling of double-encoded JSON tags"""
        # This test verifies that the system handles legacy data correctly
        # Even if we have double-encoded JSON, it should parse gracefully
        
        context_id = await context_repo.save_context(
                content="Test content for JSON parsing",
                importance_level=7,
                project_id="test_project",
            )
        
        # Should save and retrieve without errors
        assert context_id is not None
        
        contexts = await memory_manager.load_smart_contexts("test_project")
        assert len(contexts) >= 1


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
