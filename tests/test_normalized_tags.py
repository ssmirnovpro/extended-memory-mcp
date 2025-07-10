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
Unit tests for normalized tags functionality
Tests the new normalized tags schema and related operations
"""

import pytest
import pytest_asyncio
import asyncio
import tempfile
import json
from pathlib import Path
import aiosqlite

# Add project path
import sys
project_root = Path(__file__).parent.parent / "mcp-server"
sys.path.append(str(project_root))

from extended_memory_mcp.core.memory import MemoryFacade as MemoryManager  # Use new architecture

class TestNormalizedTags:
    """Tests for normalized tags functionality"""
    
    @pytest_asyncio.fixture
    async def memory_manager(self):
        """Clean memory manager with new schema"""
        with tempfile.TemporaryDirectory() as temp_dir:
            db_path = Path(temp_dir) / "test_memory.db"
            manager = MemoryManager(str(db_path))
            await manager.initialize_database()
            yield manager
    
    @pytest_asyncio.fixture
    async def memory_manager_with_data(self):
        """Memory manager with test data"""
        with tempfile.TemporaryDirectory() as temp_dir:
            db_path = Path(temp_dir) / "test_memory.db"
            manager = MemoryManager(str(db_path))
            await manager.initialize_database()
            
            # Get context repo
            context_repo = manager.context_service.context_repo
            tags_repo = manager.context_service.tags_repo
            
            # Add test contexts with tags
            context1_id = await context_repo.save_context(
                content="React component implementation",
                importance_level=8,
                project_id="test_project",
            )
            await tags_repo.save_context_tags(context1_id, ["react", "frontend", "component"])
            
            context2_id = await context_repo.save_context(
                content="Database architecture decision",
                importance_level=9,
                project_id="test_project",
            )
            await tags_repo.save_context_tags(context2_id, ["database", "architecture", "design"])
            
            context3_id = await context_repo.save_context(
                content="Frontend styling approach",
                importance_level=7,
                project_id="test_project",
            )
            await tags_repo.save_context_tags(context3_id, ["frontend", "css", "styling"])
            
            context4_id = await context_repo.save_context(
                content="Backend API implementation",
                importance_level=8,
                project_id="other_project",
            )
            await tags_repo.save_context_tags(context4_id, ["backend", "api", "python"])
            
            yield manager, {
                "context1_id": context1_id,
                "context2_id": context2_id, 
                "context3_id": context3_id,
                "context4_id": context4_id
            }
    
    @pytest.mark.asyncio
    async def test_save_context_with_tags(self, memory_manager, context_repo):
        """Test saving context with normalized tags"""
        context_id = await context_repo.save_context(
                content="Test content with tags",
                importance_level=7,
                project_id="test_project",
            )
        
        assert context_id is not None
        
        # Save tags for the context
        await memory_manager.context_service.tags_repo.save_context_tags(context_id, ["system", "memory", "config"])
        
        # Verify tags were created in normalized schema
        async with aiosqlite.connect(memory_manager.db_path) as db:
            # Check tags table
            cursor = await db.execute("SELECT COUNT(*) FROM tags")
            tag_count = (await cursor.fetchone())[0]
            assert tag_count == 3
            
            # Check context_tags table
            cursor = await db.execute("SELECT COUNT(*) FROM context_tags WHERE context_id = ?", (context_id,))
            link_count = (await cursor.fetchone())[0]
            assert link_count == 3
            
            # Check specific tags exist
            cursor = await db.execute("SELECT name FROM tags ORDER BY name")
            tag_names = [row[0] for row in await cursor.fetchall()]
            assert tag_names == ["config", "memory", "system"]
    
    @pytest.mark.asyncio
    async def test_load_contexts_with_tags(self, memory_manager_with_data):
        """Test loading contexts includes tags"""
        manager, context_ids = memory_manager_with_data
        
        contexts = await manager.context_service.context_repo.load_contexts(
            project_id="test_project", limit=10
        )
        
        assert len(contexts) == 3
        
        # Check that contexts include tags (load them manually)
        for context in contexts:
            tags = await manager.context_service.tags_repo.load_context_tags(context["id"])
            context["tags"] = tags
            assert isinstance(context["tags"], list)
            assert len(context["tags"]) > 0
        
        # Check specific context tags
        context1 = next(c for c in contexts if c["id"] == context_ids["context1_id"])
        assert set(context1["tags"]) == {"react", "frontend", "component"}
    
    @pytest.mark.asyncio
    async def test_load_contexts_by_tags_filter(self, memory_manager_with_data):
        """Test filtering contexts by tags"""
        manager, context_ids = memory_manager_with_data
        
        # Filter by single tag
        frontend_contexts = await manager.load_contexts(
            project_id="test_project",
            tags_filter=["frontend"]
        )
        
        assert len(frontend_contexts) == 2  # context1 and context3 have "frontend" tag
        
        # Filter by multiple tags (OR logic)
        react_or_css_contexts = await manager.load_contexts(
            project_id="test_project",
            tags_filter=["react", "css"]
        )
        
        assert len(react_or_css_contexts) == 2  # context1 has react, context3 has css
        
        # Filter by tag that doesn't exist
        nonexistent_contexts = await manager.load_contexts(
            project_id="test_project",
            tags_filter=["nonexistent"]
        )
        
        assert len(nonexistent_contexts) == 0
    
    @pytest.mark.asyncio
    async def test_project_isolation_with_tags(self, memory_manager_with_data):
        """Test that tag filtering respects project isolation"""
        manager, context_ids = memory_manager_with_data
        
        # Search for "backend" tag in test_project (should find nothing)
        test_project_contexts = await manager.load_contexts(
            project_id="test_project",
            tags_filter=["backend"]
        )
        assert len(test_project_contexts) == 0
        
        # Search for "backend" tag in other_project (should find context4)
        other_project_contexts = await manager.load_contexts(
            project_id="other_project",
            tags_filter=["backend"]
        )
        assert len(other_project_contexts) == 1
        assert other_project_contexts[0]["id"] == context_ids["context4_id"]
    
    @pytest.mark.asyncio
    async def test_analyze_available_tags_normalized(self, memory_manager_with_data):
        """Test tag analysis with normalized schema"""
        manager, context_ids = memory_manager_with_data
        
        result = await manager._analyze_available_tags("test_project")
        
        # Should find tags and return structured data
        assert isinstance(result, dict)
        assert "tag_analysis" in result
        assert "total_unique_tags" in result
        
        # Check tag analysis structure
        tag_analysis = result["tag_analysis"]
        assert len(tag_analysis) > 0
        
        # Find specific tags
        tag_names = [tag["tag"] for tag in tag_analysis]
        assert "frontend" in tag_names
        assert "react" in tag_names
        assert "database" in tag_names
        
        # Should not include tags from other projects
        assert "backend" not in result
        assert "python" not in result
    
    @pytest.mark.asyncio
    async def test_tag_deduplication(self, memory_manager, context_repo):
        """Test that duplicate tags are handled correctly"""
        # Save first context with tags
        context1_id = await context_repo.save_context(
                content="First context",
                importance_level=7,
                project_id="test_project",
            )
        await memory_manager.context_service.tags_repo.save_context_tags(context1_id, ["react", "frontend", "testing"])
        
        # Save second context with overlapping tags
        context2_id = await context_repo.save_context(
                content="Second context",
                importance_level=8,
                project_id="test_project",
            )
        await memory_manager.context_service.tags_repo.save_context_tags(context2_id, ["react", "testing"])
        
        async with aiosqlite.connect(memory_manager.db_path) as db:
            # Should have 3 unique tags total
            cursor = await db.execute("SELECT COUNT(*) FROM tags")
            tag_count = (await cursor.fetchone())[0]
            assert tag_count == 3
            
            # Check tag names
            cursor = await db.execute("SELECT name FROM tags ORDER BY name")
            tag_names = [row[0] for row in await cursor.fetchall()]
            assert tag_names == ["frontend", "react", "testing"]
            
            # Both contexts should link to "react" tag
            cursor = await db.execute("""
                SELECT COUNT(*) FROM context_tags ct
                JOIN tags t ON ct.tag_id = t.id
                WHERE t.name = 'react'
            """)
            react_links = (await cursor.fetchone())[0]
            assert react_links == 2
    
    @pytest.mark.asyncio
    async def test_empty_and_invalid_tags(self, memory_manager, context_repo):
        """Test handling of empty and invalid tags"""
        context_id = await context_repo.save_context(
                content="Context with mixed tags",
                importance_level=7,
                project_id="test_project",
            )
        
        assert context_id is not None
        
        # Save some valid and invalid tags (tags_repo should filter invalid ones)
        await memory_manager.context_service.tags_repo.save_context_tags(context_id, ["valid-tag", "", "another-valid", None, "   "])
        
        # Load context and check tags
        contexts = await context_repo.load_contexts(project_id="test_project")
        assert len(contexts) == 1
        
        context = contexts[0]
        # Load tags manually if they're not auto-loaded
        if "tags" not in context:
            context["tags"] = await memory_manager.context_service.tags_repo.load_context_tags(context["id"])
        
        # Should only have valid tags (empty/whitespace/None filtered out)
        assert set(context["tags"]) == {"valid-tag", "another-valid"}

    # --- New tests for get_popular_tags functionality ---

    @pytest.mark.asyncio
    async def test_get_popular_tags_with_various_usage_counts(self, memory_manager, context_repo):
        """Test get_popular_tags with tags having different usage counts"""
        # Create contexts with different tag usage patterns
        
        # Popular tag used 5 times
        for i in range(5):
            context_id = await context_repo.save_context(
                content=f"Context {i} with python",
                importance_level=7,
                project_id="test_project",
            )
            await memory_manager.context_service.tags_repo.save_context_tags(context_id, ["python"])
        
        # Moderately used tag (3 times)
        for i in range(3):
            context_id = await context_repo.save_context(
                content=f"Database context {i}",
                importance_level=6,
                project_id="test_project",
            )
            await memory_manager.context_service.tags_repo.save_context_tags(context_id, ["database"])
        
        # Recent tag used only once
        context_id = await context_repo.save_context(
            content="Testing context",
            importance_level=5,
            project_id="test_project",
        )
        await memory_manager.context_service.tags_repo.save_context_tags(context_id, ["testing"])
        
        # Get popular tags
        tags_repo = memory_manager.context_service.tags_repo
        popular_tags = await tags_repo.get_popular_tags(limit=10, min_usage=2, recent_hours=24)
        
        # Should include python(5) and database(3) as popular
        assert len(popular_tags) >= 2
        
        tag_names = [tag["tag"] for tag in popular_tags]
        tag_counts = {tag["tag"]: tag["count"] for tag in popular_tags}
        
        assert "python" in tag_names
        assert "database" in tag_names
        assert tag_counts["python"] == 5
        assert tag_counts["database"] == 3
        
        # testing(1) should also be included as recent tag
        assert "testing" in tag_names
        assert tag_counts["testing"] == 1

    @pytest.mark.asyncio
    async def test_get_popular_tags_with_min_usage_filter(self, memory_manager, context_repo):
        """Test get_popular_tags respects min_usage parameter"""
        # Create tags with known usage counts
        
        # Tag with 4 uses
        for i in range(4):
            context_id = await context_repo.save_context(
                content=f"React context {i}",
                importance_level=7,
                project_id="test_project",
            )
            await memory_manager.context_service.tags_repo.save_context_tags(context_id, ["react"])
        
        # Tag with 2 uses
        for i in range(2):
            context_id = await context_repo.save_context(
                content=f"Vue context {i}",
                importance_level=6,
                project_id="test_project",
            )
            await memory_manager.context_service.tags_repo.save_context_tags(context_id, ["vue"])
        
        # Tag with 1 use
        context_id = await context_repo.save_context(
            content="Angular context",
            importance_level=5,
            project_id="test_project",
        )
        await memory_manager.context_service.tags_repo.save_context_tags(context_id, ["angular"])
        
        tags_repo = memory_manager.context_service.tags_repo
        
        # Test with min_usage=3 and no recent tags - should only include react(4)
        popular_tags = await tags_repo.get_popular_tags(limit=10, min_usage=3, recent_hours=0)
        tag_names = [tag["tag"] for tag in popular_tags]
        assert "react" in tag_names
        assert "vue" not in tag_names
        assert "angular" not in tag_names
        
        # Test with min_usage=2 and no recent tags - should include react(4) and vue(2)
        popular_tags = await tags_repo.get_popular_tags(limit=10, min_usage=2, recent_hours=0)
        tag_names = [tag["tag"] for tag in popular_tags]
        assert "react" in tag_names
        assert "vue" in tag_names
        assert "angular" not in tag_names

    @pytest.mark.asyncio
    async def test_get_popular_tags_with_limit(self, memory_manager, context_repo):
        """Test get_popular_tags respects limit parameter"""
        # Create many tags
        tag_names = ["python", "javascript", "react", "vue", "angular", "django", "flask"]
        
        for i, tag in enumerate(tag_names):
            # Each tag used (len(tag_names) - i) times for different popularity
            for j in range(len(tag_names) - i):
                context_id = await context_repo.save_context(
                    content=f"Context for {tag} #{j}",
                    importance_level=7,
                    project_id="test_project",
                )
                await memory_manager.context_service.tags_repo.save_context_tags(context_id, [tag])
        
        tags_repo = memory_manager.context_service.tags_repo
        
        # Test with limit=3
        popular_tags = await tags_repo.get_popular_tags(limit=3, min_usage=1, recent_hours=24)
        assert len(popular_tags) <= 3
        
        # Should be ordered by usage count DESC
        if len(popular_tags) >= 2:
            assert popular_tags[0]["count"] >= popular_tags[1]["count"]

    @pytest.mark.asyncio
    async def test_get_popular_tags_complex_sql_query(self, memory_manager, context_repo):
        """Test the complex SQL query logic for popular and recent tags"""
        import time
        from datetime import datetime, timedelta
        
        tags_repo = memory_manager.context_service.tags_repo
        
        # Create a tag that's popular (>=2 uses)
        for i in range(3):
            context_id = await context_repo.save_context(
                content=f"Popular context {i}",
                importance_level=7,
                project_id="test_project",
            )
            await tags_repo.save_context_tags(context_id, ["popular"])
        
        # Test the SQL query directly
        async with memory_manager.db_manager.get_connection() as db:
            cursor = await db.execute("""
                SELECT t.name, COUNT(ct.context_id) as usage_count, MAX(c.created_at) as latest_use
                FROM tags t
                JOIN context_tags ct ON t.id = ct.tag_id
                JOIN contexts c ON ct.context_id = c.id
                GROUP BY t.id, t.name
                HAVING 
                    usage_count >= ? 
                    OR (usage_count = 1 AND datetime(latest_use) > datetime('now', '-' || ? || ' hours'))
                ORDER BY usage_count DESC, latest_use DESC
                LIMIT ?
            """, (2, 24, 10))
            
            rows = await cursor.fetchall()
            
            # Should find the popular tag
            assert len(rows) >= 1
            assert rows[0][0] == "popular"  # tag name
            assert rows[0][1] == 3  # usage count

    @pytest.mark.asyncio
    async def test_get_popular_tags_empty_database(self, memory_manager):
        """Test get_popular_tags with empty database"""
        tags_repo = memory_manager.context_service.tags_repo
        
        popular_tags = await tags_repo.get_popular_tags(limit=10, min_usage=1, recent_hours=24)
        
        assert popular_tags == []

    @pytest.mark.asyncio
    async def test_get_popular_tags_configuration_loading(self, memory_manager, context_repo):
        """Test get_popular_tags loads configuration correctly"""
        # Create some test data
        context_id = await context_repo.save_context(
            content="Test context",
            importance_level=7,
            project_id="test_project",
        )
        await memory_manager.context_service.tags_repo.save_context_tags(context_id, ["test"])
        
        tags_repo = memory_manager.context_service.tags_repo
        
        # Test with None parameters (should use config defaults)
        popular_tags = await tags_repo.get_popular_tags(limit=None, min_usage=None, recent_hours=None)
        
        # Should not crash and return results
        assert isinstance(popular_tags, list)
        
        # Test with explicit parameters
        popular_tags = await tags_repo.get_popular_tags(limit=5, min_usage=1, recent_hours=12)
        
        assert isinstance(popular_tags, list)

    @pytest.mark.asyncio
    async def test_get_popular_tags_error_handling(self, memory_manager):
        """Test error handling in get_popular_tags"""
        tags_repo = memory_manager.context_service.tags_repo
        
        # Mock the database manager to simulate an error without async warning
        from unittest.mock import Mock
        
        def failing_get_connection():
            raise Exception("Database connection error")
        
        # Replace get_connection with a sync function that raises
        original_get_connection = tags_repo.db_manager.get_connection
        tags_repo.db_manager.get_connection = failing_get_connection
        
        try:
            # Should handle the error gracefully
            popular_tags = await tags_repo.get_popular_tags()
            assert popular_tags == []
        finally:
            # Restore original method
            tags_repo.db_manager.get_connection = original_get_connection

    @pytest.mark.asyncio
    async def test_get_popular_tags_with_project_id_filter(self, memory_manager):
        """Test get_popular_tags with project_id filtering"""
        # Save contexts in different projects
        project_a_id = await memory_manager.save_context(
            project_id="project_a",
            content="Content A1",
            importance_level=7,
            tags=["python", "api", "backend"]
        )
        
        await memory_manager.save_context(
            project_id="project_a", 
            content="Content A2",
            importance_level=6,
            tags=["python", "web", "backend"]
        )
        
        await memory_manager.save_context(
            project_id="project_b",
            content="Content B1", 
            importance_level=8,
            tags=["javascript", "frontend", "react"]
        )
        
        await memory_manager.save_context(
            project_id="project_b",
            content="Content B2",
            importance_level=7,
            tags=["javascript", "api", "node"]
        )
        
        tags_repo = memory_manager.context_service.tags_repo
        
        # Test project_a tags
        project_a_tags = await tags_repo.get_popular_tags(
            limit=10, min_usage=1, project_id="project_a"
        )
        
        project_a_tag_names = {tag["tag"] for tag in project_a_tags}
        
        # Project A should have its own tags
        assert "python" in project_a_tag_names
        assert "backend" in project_a_tag_names
        assert "api" in project_a_tag_names
        assert "web" in project_a_tag_names
        
        # Project A should NOT have project B tags
        assert "javascript" not in project_a_tag_names
        assert "frontend" not in project_a_tag_names
        assert "react" not in project_a_tag_names
        assert "node" not in project_a_tag_names
        
        # Test project_b tags
        project_b_tags = await tags_repo.get_popular_tags(
            limit=10, min_usage=1, project_id="project_b"
        )
        
        project_b_tag_names = {tag["tag"] for tag in project_b_tags}
        
        # Project B should have its own tags
        assert "javascript" in project_b_tag_names
        assert "frontend" in project_b_tag_names
        assert "react" in project_b_tag_names
        assert "node" in project_b_tag_names
        
        # Project B should NOT have project A tags (except shared ones)
        assert "python" not in project_b_tag_names
        assert "web" not in project_b_tag_names
        
        # Shared tag "api" should appear in both but with different counts
        project_a_api = next((tag for tag in project_a_tags if tag["tag"] == "api"), None)
        project_b_api = next((tag for tag in project_b_tags if tag["tag"] == "api"), None)
        
        assert project_a_api is not None
        assert project_b_api is not None
        assert project_a_api["count"] == 1  # Used once in project A
        assert project_b_api["count"] == 1  # Used once in project B

    @pytest.mark.asyncio 
    async def test_get_popular_tags_project_isolation_complete(self, memory_manager):
        """Test complete isolation between projects"""
        # Create tags that could be confused between projects
        await memory_manager.save_context(
            project_id="dev_project",
            content="Development work",
            importance_level=7,
            tags=["development", "coding", "bug-fix", "feature"]
        )
        
        await memory_manager.save_context(
            project_id="test_project", 
            content="Testing work",
            importance_level=7,
            tags=["testing", "qa", "bug-fix", "validation"]
        )
        
        tags_repo = memory_manager.context_service.tags_repo
        
        # Get tags for each project
        dev_tags = await tags_repo.get_popular_tags(
            limit=20, min_usage=1, project_id="dev_project"
        )
        
        test_tags = await tags_repo.get_popular_tags(
            limit=20, min_usage=1, project_id="test_project"
        )
        
        dev_tag_names = {tag["tag"] for tag in dev_tags}
        test_tag_names = {tag["tag"] for tag in test_tags}
        
        # Check dev project tags
        assert "development" in dev_tag_names
        assert "coding" in dev_tag_names
        assert "feature" in dev_tag_names
        assert "bug-fix" in dev_tag_names  # Shared tag
        
        # Check test project tags
        assert "testing" in test_tag_names
        assert "qa" in test_tag_names
        assert "validation" in test_tag_names  
        assert "bug-fix" in test_tag_names  # Shared tag
        
        # Verify isolation (no cross-contamination)
        assert "development" not in test_tag_names
        assert "coding" not in test_tag_names
        assert "feature" not in test_tag_names
        
        assert "testing" not in dev_tag_names
        assert "qa" not in dev_tag_names
        assert "validation" not in dev_tag_names
        
        # Verify shared tag appears in both with correct counts
        dev_bug_fix = next(tag for tag in dev_tags if tag["tag"] == "bug-fix")
        test_bug_fix = next(tag for tag in test_tags if tag["tag"] == "bug-fix")
        
        assert dev_bug_fix["count"] == 1
        assert test_bug_fix["count"] == 1

    @pytest.mark.asyncio
    async def test_get_popular_tags_without_project_id_shows_all(self, memory_manager):
        """Test that get_popular_tags without project_id shows all tags"""
        # Create contexts in multiple projects
        await memory_manager.save_context(
            project_id="alpha",
            content="Alpha content",
            importance_level=7,
            tags=["alpha-tag", "shared-tag"]
        )
        
        await memory_manager.save_context(
            project_id="beta",
            content="Beta content", 
            importance_level=7,
            tags=["beta-tag", "shared-tag"]
        )
        
        tags_repo = memory_manager.context_service.tags_repo
        
        # Get all tags (no project filter)
        all_tags = await tags_repo.get_popular_tags(limit=20, min_usage=1, project_id=None)
        all_tag_names = {tag["tag"] for tag in all_tags}
        
        # Should contain tags from both projects
        assert "alpha-tag" in all_tag_names
        assert "beta-tag" in all_tag_names
        assert "shared-tag" in all_tag_names
        
        # Shared tag should have combined count
        shared_tag = next(tag for tag in all_tags if tag["tag"] == "shared-tag")
        assert shared_tag["count"] == 2  # Used in both projects


class TestTagsRepositoryEdgeCases:
    """Test edge cases for project_id filtering"""

    @pytest.mark.asyncio
    async def test_get_popular_tags_empty_project_id(self, memory_manager):
        """Test get_popular_tags with empty string project_id"""
        # Create context with empty project_id
        await memory_manager.save_context(
            project_id="",
            content="Empty project content",
            importance_level=7,
            tags=["empty-project", "edge-case"]
        )
        
        tags_repo = memory_manager.context_service.tags_repo
        
        # Test with empty string project_id
        empty_tags = await tags_repo.get_popular_tags(
            limit=10, min_usage=1, project_id=""
        )
        
        empty_tag_names = {tag["tag"] for tag in empty_tags}
        assert "empty-project" in empty_tag_names
        assert "edge-case" in empty_tag_names

    @pytest.mark.asyncio
    async def test_get_popular_tags_special_characters_project_id(self, memory_manager):
        """Test get_popular_tags with special characters in project_id"""
        special_project_ids = [
            "project-with-dashes",
            "project_with_underscores", 
            "project.with.dots",
            "project@with#symbols",
            "проект-с-unicode",
            "project with spaces"
        ]
        
        # Create contexts for each special project_id
        for i, project_id in enumerate(special_project_ids):
            await memory_manager.save_context(
                project_id=project_id,
                content=f"Content for {project_id}",
                importance_level=7,
                tags=[f"tag-{i}", "special-char"]
            )
        
        tags_repo = memory_manager.context_service.tags_repo
        
        # Test each special project_id
        for i, project_id in enumerate(special_project_ids):
            tags = await tags_repo.get_popular_tags(
                limit=10, min_usage=1, project_id=project_id
            )
            
            tag_names = {tag["tag"] for tag in tags}
            assert f"tag-{i}" in tag_names
            assert "special-char" in tag_names
            
            # Verify isolation - other special tags should not appear
            other_tags = [f"tag-{j}" for j in range(len(special_project_ids)) if j != i]
            for other_tag in other_tags:
                assert other_tag not in tag_names

    @pytest.mark.asyncio 
    async def test_get_popular_tags_very_long_project_id(self, memory_manager):
        """Test get_popular_tags with extremely long project_id"""
        # Create very long project_id (1000 characters)
        long_project_id = "x" * 1000
        
        await memory_manager.save_context(
            project_id=long_project_id,
            content="Content with very long project ID",
            importance_level=8,
            tags=["long-project", "stress-test"]
        )
        
        tags_repo = memory_manager.context_service.tags_repo
        
        # Should handle long project_id gracefully
        tags = await tags_repo.get_popular_tags(
            limit=10, min_usage=1, project_id=long_project_id
        )
        
        tag_names = {tag["tag"] for tag in tags}
        assert "long-project" in tag_names
        assert "stress-test" in tag_names

    @pytest.mark.asyncio
    async def test_get_popular_tags_sql_injection_attempt(self, memory_manager):
        """Test get_popular_tags with potential SQL injection in project_id"""
        sql_injection_attempts = [
            "'; DROP TABLE contexts; --",
            "' OR '1'='1",
            "'; SELECT * FROM contexts; --",
            "project' UNION SELECT * FROM tags --",
            "'; DELETE FROM contexts WHERE project_id='test'; --"
        ]
        
        tags_repo = memory_manager.context_service.tags_repo
        
        # Create legitimate context first
        await memory_manager.save_context(
            project_id="legitimate_project",
            content="Legitimate content",
            importance_level=7,
            tags=["legitimate", "safe"]
        )
        
        # Test each SQL injection attempt
        for injection_attempt in sql_injection_attempts:
            # Should return empty results (no contexts with these project_ids)
            # and not crash or execute malicious SQL
            tags = await tags_repo.get_popular_tags(
                limit=10, min_usage=1, project_id=injection_attempt
            )
            
            # Should return empty list, not crash
            assert isinstance(tags, list)
            assert len(tags) == 0
        
        # Verify legitimate data is still intact
        legitimate_tags = await tags_repo.get_popular_tags(
            limit=10, min_usage=1, project_id="legitimate_project"
        )
        
        legitimate_tag_names = {tag["tag"] for tag in legitimate_tags}
        assert "legitimate" in legitimate_tag_names
        assert "safe" in legitimate_tag_names

    @pytest.mark.asyncio
    async def test_get_popular_tags_null_and_none_project_id(self, memory_manager):
        """Test get_popular_tags with None and null-like project_id values"""
        # Test various null-like values
        null_like_values = [
            None,
            "null", 
            "NULL",
            "None",
            "undefined"
        ]
        
        tags_repo = memory_manager.context_service.tags_repo
        
        # Create context with string "null" as project_id  
        await memory_manager.save_context(
            project_id="null",
            content="Content with null string project_id",
            importance_level=7,
            tags=["null-string", "edge-case"]
        )
        
        # Test None (should return all tags)
        none_tags = await tags_repo.get_popular_tags(
            limit=20, min_usage=1, project_id=None
        )
        assert isinstance(none_tags, list)
        # Should include tags from all projects
        
        # Test string "null" (should filter to only that project)
        null_string_tags = await tags_repo.get_popular_tags(
            limit=10, min_usage=1, project_id="null"
        )
        
        null_tag_names = {tag["tag"] for tag in null_string_tags}
        assert "null-string" in null_tag_names
        assert "edge-case" in null_tag_names

    @pytest.mark.asyncio
    async def test_get_popular_tags_whitespace_project_id(self, memory_manager):
        """Test get_popular_tags with whitespace-only project_id"""
        whitespace_project_ids = [
            " ",           # Single space
            "   ",         # Multiple spaces  
            "\t",          # Tab
            "\n",          # Newline
            "\r\n",        # Windows line ending
            "  \t  \n  "   # Mixed whitespace
        ]
        
        # Create contexts for whitespace project_ids
        for i, project_id in enumerate(whitespace_project_ids):
            await memory_manager.save_context(
                project_id=project_id,
                content=f"Content for whitespace project {i}",
                importance_level=7,
                tags=[f"whitespace-{i}", "space-test"]
            )
        
        tags_repo = memory_manager.context_service.tags_repo
        
        # Test each whitespace project_id
        for i, project_id in enumerate(whitespace_project_ids):
            tags = await tags_repo.get_popular_tags(
                limit=10, min_usage=1, project_id=project_id
            )
            
            tag_names = {tag["tag"] for tag in tags}
            assert f"whitespace-{i}" in tag_names
            assert "space-test" in tag_names


    # --- Tests for multiple tags filtering functionality ---

    @pytest.mark.asyncio
    async def test_find_contexts_by_multiple_tags_basic(self, memory_manager, context_repo):
        """Test basic multiple tags filtering with OR logic"""
        # Create contexts with different tag combinations
        context1_id = await context_repo.save_context(
            content="Frontend React content", 
            importance_level=7, 
            project_id="web_app"
        )
        await memory_manager.context_service.tags_repo.save_context_tags(
            context1_id, ["react", "frontend"]
        )
        
        context2_id = await context_repo.save_context(
            content="Backend API content", 
            importance_level=8, 
            project_id="web_app"
        )
        await memory_manager.context_service.tags_repo.save_context_tags(
            context2_id, ["api", "backend"]
        )
        
        context3_id = await context_repo.save_context(
            content="Database setup", 
            importance_level=6, 
            project_id="web_app"
        )
        await memory_manager.context_service.tags_repo.save_context_tags(
            context3_id, ["database", "postgres"]
        )
        
        tags_repo = memory_manager.context_service.tags_repo
        
        # Test OR logic: contexts with ANY of the specified tags
        result_ids = await tags_repo.find_contexts_by_multiple_tags(
            tags=["react", "api"], 
            project_id="web_app"
        )
        
        # Should find contexts 1 and 2 (they have react OR api)
        assert len(result_ids) == 2
        assert context1_id in result_ids
        assert context2_id in result_ids
        assert context3_id not in result_ids

    @pytest.mark.asyncio 
    async def test_find_contexts_by_multiple_tags_empty_input(self, memory_manager):
        """Test multiple tags filtering with empty/invalid input"""
        tags_repo = memory_manager.context_service.tags_repo
        
        # Empty tags list
        result = await tags_repo.find_contexts_by_multiple_tags(tags=[])
        assert result == []
        
        # Tags with only whitespace
        result = await tags_repo.find_contexts_by_multiple_tags(tags=["", "   ", "\t"])
        assert result == []
        
        # Mixed valid and invalid tags
        context_id = await memory_manager.save_context(
            content="Test content", 
            importance_level=7, 
            tags=["valid-tag"]
        )
        
        result = await tags_repo.find_contexts_by_multiple_tags(
            tags=["valid-tag", "", "  "]
        )
        assert len(result) == 1
        assert context_id in result

    @pytest.mark.asyncio
    async def test_find_contexts_by_multiple_tags_case_insensitive(self, memory_manager):
        """Test that multiple tags search is case insensitive"""
        context_id = await memory_manager.save_context(
            content="Case test content",
            importance_level=7, 
            tags=["ReactJS", "FRONTEND", "api-DESIGN"]
        )
        
        tags_repo = memory_manager.context_service.tags_repo
        
        # Search with different cases should find the same context
        test_cases = [
            ["reactjs", "frontend"],
            ["REACTJS", "frontend"],
            ["ReactJS", "FRONTEND"],
            ["api-design", "REACTJS"]
        ]
        
        for tags in test_cases:
            result = await tags_repo.find_contexts_by_multiple_tags(tags=tags)
            assert len(result) == 1
            assert context_id in result

    @pytest.mark.asyncio
    async def test_find_contexts_by_multiple_tags_project_isolation(self, memory_manager):
        """Test that multiple tags filtering respects project isolation"""
        # Create contexts in different projects with same tags
        context1_id = await memory_manager.save_context(
            project_id="project_a",
            content="Project A content",
            importance_level=7,
            tags=["shared-tag", "project-a-specific"]
        )
        
        context2_id = await memory_manager.save_context(
            project_id="project_b", 
            content="Project B content",
            importance_level=7,
            tags=["shared-tag", "project-b-specific"]
        )
        
        tags_repo = memory_manager.context_service.tags_repo
        
        # Search in project A should only return project A context
        result_a = await tags_repo.find_contexts_by_multiple_tags(
            tags=["shared-tag"], 
            project_id="project_a"
        )
        assert len(result_a) == 1
        assert context1_id in result_a
        assert context2_id not in result_a
        
        # Search in project B should only return project B context  
        result_b = await tags_repo.find_contexts_by_multiple_tags(
            tags=["shared-tag"],
            project_id="project_b"
        )
        assert len(result_b) == 1
        assert context2_id in result_b
        assert context1_id not in result_b
        
        # Search without project filter should return both
        result_all = await tags_repo.find_contexts_by_multiple_tags(
            tags=["shared-tag"],
            project_id=None
        )
        assert len(result_all) == 2
        assert context1_id in result_all
        assert context2_id in result_all

    @pytest.mark.asyncio
    async def test_find_contexts_by_multiple_tags_nonexistent_tags(self, memory_manager):
        """Test multiple tags filtering with nonexistent tags"""
        # Create some contexts with real tags
        await memory_manager.save_context(
            content="Real content", 
            importance_level=7,
            tags=["real-tag", "another-real-tag"]
        )
        
        tags_repo = memory_manager.context_service.tags_repo
        
        # Search for tags that don't exist
        result = await tags_repo.find_contexts_by_multiple_tags(
            tags=["nonexistent-tag", "also-fake"]
        )
        assert result == []
        
        # Mix of real and fake tags - should find contexts with real tags
        context_id = await memory_manager.save_context(
            content="Mixed content",
            importance_level=8, 
            tags=["real-tag-2"]
        )
        
        result = await tags_repo.find_contexts_by_multiple_tags(
            tags=["real-tag-2", "fake-tag"]
        )
        assert len(result) == 1
        assert context_id in result

    @pytest.mark.asyncio
    async def test_find_contexts_by_multiple_tags_limit(self, memory_manager):
        """Test that multiple tags filtering respects limit parameter"""
        # Create many contexts with the same tag
        context_ids = []
        for i in range(10):
            context_id = await memory_manager.save_context(
                content=f"Content {i}",
                importance_level=7,
                tags=["common-tag"]
            )
            context_ids.append(context_id)
        
        tags_repo = memory_manager.context_service.tags_repo
        
        # Test different limits
        result_3 = await tags_repo.find_contexts_by_multiple_tags(
            tags=["common-tag"], 
            limit=3
        )
        assert len(result_3) == 3
        
        result_5 = await tags_repo.find_contexts_by_multiple_tags(
            tags=["common-tag"],
            limit=5
        )
        assert len(result_5) == 5
        
        # All results should be from our created contexts
        for ctx_id in result_3:
            assert ctx_id in context_ids
