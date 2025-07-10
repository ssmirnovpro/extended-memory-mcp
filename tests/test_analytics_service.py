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
Unit tests for AnalyticsService - Statistics and memory analysis
"""
import pytest
import pytest_asyncio
import tempfile
import os
from pathlib import Path
import sys

# Add project to path
project_root = Path(__file__).parent.parent / "mcp-server"
sys.path.append(str(project_root))

from extended_memory_mcp.core.memory.database_manager import DatabaseManager
from extended_memory_mcp.core.memory.context_repository import ContextRepository
from extended_memory_mcp.core.memory.tags_repository import TagsRepository
from extended_memory_mcp.core.memory.services.analytics_service import AnalyticsService


class TestAnalyticsService:
    """Test AnalyticsService functionality"""
    
    @pytest_asyncio.fixture
    async def analytics_service(self):
        """Create AnalyticsService with temporary database and some test data"""
        # Create temporary database
        db_file = tempfile.NamedTemporaryFile(delete=False, suffix='.db')
        db_path = db_file.name
        db_file.close()
        
        try:
            db_manager = DatabaseManager(db_path)
            await db_manager.ensure_database()
            
            context_repo = ContextRepository(db_manager)
            tags_repo = TagsRepository(db_manager)
            service = AnalyticsService(db_manager, context_repo, tags_repo)
            
            yield service, context_repo, tags_repo
            
        finally:
            # Cleanup
            if os.path.exists(db_path):
                os.unlink(db_path)

    @pytest.mark.asyncio
    async def test_get_database_stats_empty(self, analytics_service):
        """Test database stats with empty database"""
        service, _, _ = analytics_service
        
        stats = await service.get_database_stats()
        
        assert stats["active_contexts"] == 0
        assert stats["active_projects"] == 0
        assert stats["total_tags"] == 0
        assert stats["database_size_bytes"] >= 0
        assert stats["database_size_mb"] >= 0
        assert stats["oldest_context"] is None
        assert stats["newest_context"] is None
        assert "database_path" in stats
        assert stats["context_types"] == [{"type": "context", "count": 0}]  # Updated format
        assert stats["importance_levels"] == []

    @pytest.mark.asyncio
    async def test_get_database_stats_with_data(self, analytics_service):
        """Test database stats with actual data"""
        service, context_repo, tags_repo = analytics_service
        
        # Create test contexts  
        context_id1 = await context_repo.save_context(
                content="First context",
                importance_level=8,
                project_id="test_proj"
            )
        
        context_id2 = await context_repo.save_context(
                content="Second context",
                importance_level=6,
                project_id="test_proj"
            )
        
        # Add tags
        await tags_repo.save_context_tags(context_id1, ["python", "coding", "technical"])
        await tags_repo.save_context_tags(context_id2, ["architecture", "decision"])
        
        # Get stats
        stats = await service.get_database_stats()
        
        assert stats["active_contexts"] == 2
        assert stats["active_projects"] == 1
        assert stats["total_tags"] == 5
        assert stats["oldest_context"] is not None
        assert stats["newest_context"] is not None
        
        # Check importance distribution
        importance_levels = [i["level"] for i in stats["importance_levels"]]
        assert 8 in importance_levels
        assert 6 in importance_levels

    @pytest.mark.asyncio
    async def test_get_memory_stats_empty_project(self, analytics_service):
        """Test memory stats for empty project"""
        service, _, _ = analytics_service
        
        stats = await service.get_memory_stats("empty_project")
        
        assert stats["project_id"] == "empty_project"
        assert stats["total_contexts"] == 0
        assert stats["contexts_loaded"] == 0
        assert stats["avg_importance"] == 0
        assert stats["latest_context"] is None
        assert stats["tag_distribution"] == []
        assert stats["importance_levels"] == []
        assert stats["recent_activity_7d"] == 0

    @pytest.mark.asyncio
    async def test_get_memory_stats_with_data(self, analytics_service, context_repo):
        """Test memory stats with project data"""
        service, context_repo, tags_repo = analytics_service
        
        # Create test contexts
        await context_repo.save_context(
                content="Context 1",
                importance_level=9,
                project_id="data_project"
            )
        await context_repo.save_context(
                content="Context 2",
                importance_level=7,
                project_id="data_project"
            )
        await context_repo.save_context(
                content="Context 3",
                importance_level=5,
                project_id="data_project"
            )
        
        stats = await service.get_memory_stats("data_project")
        
        assert stats["project_id"] == "data_project"
        assert stats["total_contexts"] == 3
        assert stats["contexts_loaded"] <= 3
        # Loaded contexts might be filtered by default importance_level >= 7
        # so we get [9, 7] with average 8.0
        assert stats["avg_importance"] == 8.0
        assert stats["latest_context"] is not None
        assert "tag_distribution" in stats  # Updated from context_types

    @pytest.mark.asyncio
    async def test_analyze_tag_patterns_empty(self, analytics_service):
        """Test tag pattern analysis with no data"""
        service, _, _ = analytics_service
        
        analysis = await service.analyze_tag_patterns()
        
        assert "tag_analysis" in analysis
        assert analysis["tag_analysis"] == []
        assert analysis["total_unique_tags"] == 0
        assert "analysis_timestamp" in analysis

    @pytest.mark.asyncio
    async def test_analyze_tag_patterns_with_data(self, analytics_service, context_repo):
        """Test tag pattern analysis with actual data"""
        service, context_repo, tags_repo = analytics_service
        
        # Create contexts with tags
        context_id1 = await context_repo.save_context(
                content="Content 1",
                importance_level=8,
                project_id="proj1"
            )
        context_id2 = await context_repo.save_context(
                content="Content 2",
                importance_level=7,
                project_id="proj1"
            )
        context_id3 = await context_repo.save_context(
                content="Content 3",
                importance_level=6,
                project_id="proj2"
            )
        
        # Add overlapping tags
        await tags_repo.save_context_tags(context_id1, ["python", "backend"])
        await tags_repo.save_context_tags(context_id2, ["python", "api"])  # python appears twice
        await tags_repo.save_context_tags(context_id3, ["frontend", "react"])
        
        analysis = await service.analyze_tag_patterns()
        
        assert len(analysis["tag_analysis"]) == 5  # python, backend, api, frontend, react
        
        # Find python tag (should have highest usage)
        python_tag = next((t for t in analysis["tag_analysis"] if t["tag"] == "python"), None)
        assert python_tag is not None
        assert python_tag["usage_count"] == 2
        assert python_tag["avg_importance"] == 7.5  # (8+7)/2

    @pytest.mark.asyncio
    async def test_get_system_health_good(self, analytics_service, context_repo):
        """Test system health with good conditions"""
        service, context_repo, tags_repo = analytics_service
        
        # Create some normal data
        context_id = await context_repo.save_context(
                content="Normal context",
                importance_level=7,
                project_id="proj1"
            )
        await tags_repo.save_context_tags(context_id, ["normal", "tag"])
        
        health = await service.get_system_health()
        
        assert health["health_score"] >= 70  # Should be good
        assert health["status"] in ["excellent", "good"]
        assert "database_stats" in health
        assert "issues" in health
        assert "recommendations" in health
        assert "last_check" in health
        assert len(health["issues"]) == 0  # No issues with small, normal data

    @pytest.mark.asyncio
    async def test_get_system_health_with_issues(self, analytics_service, context_repo):
        """Test system health detection of issues"""
        service, context_repo, tags_repo = analytics_service
        
        # Create many contexts without tags (should trigger warning)
        for i in range(10):
            await context_repo.save_context(
                content=f"Untagged context {i}",
                importance_level=5,
                project_id="proj1"
            )
        
        # Create unused tags
        for tag_name in ["unused1", "unused2", "unused3"]:
            # Insert tags directly to make them unused
            async with service.db_manager.get_connection() as db:
                await db.execute("INSERT INTO tags (name) VALUES (?)", (tag_name,))
                await db.commit()
        
        health = await service.get_system_health()
        
        # Should detect issues
        assert len(health["issues"]) > 0
        assert health["health_score"] < 100
        
        # Check for specific issues
        issue_text = " ".join(health["issues"])
        assert "without tags" in issue_text or "Unused tags" in issue_text
