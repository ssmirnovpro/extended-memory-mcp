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
Tests for the new load_contexts_by_ids functionality added in SQL optimization refactoring.
"""

import pytest
import tempfile
import os
from unittest.mock import Mock, AsyncMock

from extended_memory_mcp.core.memory import MemoryFacade as MemoryManager
from extended_memory_mcp.core.memory.context_repository import ContextRepository
from extended_memory_mcp.core.memory.tags_repository import TagsRepository  
from extended_memory_mcp.core.memory.database_manager import DatabaseManager


class TestLoadContextsByIds:
    """Test the new load_contexts_by_ids optimization method."""

    @pytest.fixture
    async def memory_manager_with_contexts(self):
        """Create memory manager with test contexts for load_contexts_by_ids testing."""
        # Create temporary database
        db_fd, db_path = tempfile.mkstemp(suffix='.db')
        os.close(db_fd)
        
        try:
            manager = MemoryManager(db_path=db_path)
            await manager.initialize_database()
            
            # Get context repository from manager
            context_repo = manager.context_service.context_repo
            
            # Get context repository from manager
            context_repo = manager.context_service.context_repo
            
            # Create test contexts with different projects and types
            context_ids = {}
            
            # Project A contexts
            context_ids['ctx1'] = await context_repo.save_context(
                content="Context 1 in project A",
                importance_level=8,
                project_id="project_a"
            )
            
            context_ids['ctx2'] = await context_repo.save_context(
                content="Context 2 in project A",
                importance_level=6,
                project_id="project_a"
            )
            
            # Project B contexts
            context_ids['ctx3'] = await context_repo.save_context(
                content="Context 3 in project B",
                importance_level=9,
                project_id="project_b"
            )
            
            context_ids['ctx4'] = await context_repo.save_context(
                content="Context 4 in project B",
                importance_level=7,
                project_id="project_b"
            )
            
            yield manager, context_ids
            
        finally:
            if os.path.exists(db_path):
                os.unlink(db_path)

    @pytest.mark.asyncio
    async def test_context_repository_load_contexts_by_ids_basic(self, memory_manager_with_contexts, context_repo):
        """Test ContextRepository.load_contexts_by_ids basic functionality."""
        manager, context_ids = memory_manager_with_contexts
        
        # Test loading specific contexts by IDs
        target_ids = [context_ids['ctx1'], context_ids['ctx3']]
        contexts = await manager.context_service.context_repo.load_contexts_by_ids(target_ids)
        
        assert len(contexts) == 2
        
        # Verify correct contexts were loaded
        loaded_ids = [ctx['id'] for ctx in contexts]
        assert context_ids['ctx1'] in loaded_ids
        assert context_ids['ctx3'] in loaded_ids
        
        # Verify context data integrity
        for context in contexts:
            if context['id'] == context_ids['ctx1']:
                assert context['content'] == "Context 1 in project A"
                assert context['project_id'] == "project_a"
                assert context['importance_level'] == 8
            elif context['id'] == context_ids['ctx3']:
                assert context['content'] == "Context 3 in project B"
                assert context['project_id'] == "project_b"
                assert context['importance_level'] == 9

    @pytest.mark.asyncio
    async def test_context_repository_load_contexts_by_ids_empty_list(self, memory_manager_with_contexts, context_repo):
        """Test load_contexts_by_ids with empty ID list."""
        manager, _ = memory_manager_with_contexts
        
        contexts = await manager.context_service.context_repo.load_contexts_by_ids([])
        assert len(contexts) == 0

    @pytest.mark.asyncio
    async def test_context_repository_load_contexts_by_ids_nonexistent_ids(self, memory_manager_with_contexts, context_repo):
        """Test load_contexts_by_ids with non-existent IDs."""
        manager, _ = memory_manager_with_contexts
        
        # Use IDs that don't exist
        nonexistent_ids = [9999, 8888, 7777]
        contexts = await manager.context_service.context_repo.load_contexts_by_ids(nonexistent_ids)
        
        assert len(contexts) == 0

    @pytest.mark.asyncio 
    async def test_context_repository_load_contexts_by_ids_mixed_existing_nonexistent(self, memory_manager_with_contexts, context_repo):
        """Test load_contexts_by_ids with mix of existing and non-existent IDs."""
        manager, context_ids = memory_manager_with_contexts
        
        # Mix existing and non-existent IDs
        mixed_ids = [context_ids['ctx1'], 9999, context_ids['ctx2'], 8888]
        contexts = await manager.context_service.context_repo.load_contexts_by_ids(mixed_ids)
        
        # Should return only existing contexts
        assert len(contexts) == 2
        loaded_ids = [ctx['id'] for ctx in contexts]
        assert context_ids['ctx1'] in loaded_ids
        assert context_ids['ctx2'] in loaded_ids

    @pytest.mark.asyncio
    async def test_context_repository_load_contexts_by_ids_ordering(self, memory_manager_with_contexts, context_repo):
        """Test that load_contexts_by_ids returns contexts ordered by creation time."""
        manager, context_ids = memory_manager_with_contexts
        
        # Load all contexts
        all_ids = list(context_ids.values())
        contexts = await manager.context_service.context_repo.load_contexts_by_ids(all_ids)
        
        assert len(contexts) == 4
        
        # Verify ordering: created_at DESC (newest first)
        # Newer contexts should come first
        for i in range(len(contexts) - 1):
            current_time = contexts[i]['created_at']
            next_time = contexts[i + 1]['created_at']
            assert current_time >= next_time, f"Context {i} ({current_time}) should be newer than context {i+1} ({next_time})"


class TestTagsRepositoryProjectFilter:
    """Test the enhanced find_contexts_by_tag with project_id parameter."""

    @pytest.fixture
    async def tags_manager_with_data(self):
        """Create database with contexts across multiple projects for tag testing."""
        db_fd, db_path = tempfile.mkstemp(suffix='.db')
        os.close(db_fd)
        
        try:
            manager = MemoryManager(db_path=db_path)
            await manager.initialize_database()
            
            # Get repositories from manager
            context_repo = manager.context_service.context_repo
            tags_repo = manager.context_service.tags_repo
            
            # Project A contexts
            ctx1_id = await context_repo.save_context(
                content="SQL optimization in project A",
                importance_level=8,
                project_id="project_a"
            )
            
            ctx2_id = await context_repo.save_context(
                content="Architecture decision in project A",
                importance_level=7,
                project_id="project_a",
            )
            
            # Project B contexts  
            ctx3_id = await context_repo.save_context(
                content="SQL refactoring in project B",
                importance_level=9,
                project_id="project_b",
            )
            
            ctx4_id = await context_repo.save_context(
                content="Performance testing in project B",
                importance_level=6,
                project_id="project_b",
            )
            
            context_ids = {
                'project_a_sql': ctx1_id,
                'project_a_arch': ctx2_id, 
                'project_b_sql': ctx3_id,
                'project_b_perf': ctx4_id
            }
            
            # Add tags for each context (according to test expectations)
            await tags_repo.save_context_tags(ctx1_id, ["sql", "optimization", "performance", "technical"])
            await tags_repo.save_context_tags(ctx2_id, ["architecture", "decision"])
            await tags_repo.save_context_tags(ctx3_id, ["sql", "refactoring", "performance", "technical"])
            await tags_repo.save_context_tags(ctx4_id, ["performance", "testing"])
            
            yield manager, context_ids
            
        finally:
            if os.path.exists(db_path):
                os.unlink(db_path)

    @pytest.mark.asyncio
    async def test_find_contexts_by_tag_without_project_filter(self, tags_manager_with_data):
        """Test find_contexts_by_tag without project filter (original behavior)."""
        manager, context_ids = tags_manager_with_data
        
        # Find all contexts with "sql" tag across all projects
        sql_context_ids = await manager.context_service.tags_repo.find_contexts_by_tag("sql")
        
        assert len(sql_context_ids) == 2
        assert context_ids['project_a_sql'] in sql_context_ids
        assert context_ids['project_b_sql'] in sql_context_ids

    @pytest.mark.asyncio  
    async def test_find_contexts_by_tag_with_project_filter(self, tags_manager_with_data):
        """Test find_contexts_by_tag with project_id filter (new functionality)."""
        manager, context_ids = tags_manager_with_data
        
        # Find "sql" tag contexts only in project_a
        project_a_sql_ids = await manager.context_service.tags_repo.find_contexts_by_tag("sql", project_id="project_a")
        
        assert len(project_a_sql_ids) == 1
        assert context_ids['project_a_sql'] in project_a_sql_ids
        assert context_ids['project_b_sql'] not in project_a_sql_ids
        
        # Find "sql" tag contexts only in project_b  
        project_b_sql_ids = await manager.context_service.tags_repo.find_contexts_by_tag("sql", project_id="project_b")
        
        assert len(project_b_sql_ids) == 1
        assert context_ids['project_b_sql'] in project_b_sql_ids
        assert context_ids['project_a_sql'] not in project_b_sql_ids

    @pytest.mark.asyncio
    async def test_find_contexts_by_tag_project_filter_no_results(self, tags_manager_with_data):
        """Test find_contexts_by_tag with project filter that has no matching contexts."""
        manager, _ = tags_manager_with_data
        
        # Search for tag that doesn't exist in the specified project
        results = await manager.context_service.tags_repo.find_contexts_by_tag("architecture", project_id="project_b")
        
        assert len(results) == 0

    @pytest.mark.asyncio
    async def test_find_contexts_by_tag_nonexistent_project(self, tags_manager_with_data):
        """Test find_contexts_by_tag with non-existent project_id."""
        manager, _ = tags_manager_with_data
        
        results = await manager.context_service.tags_repo.find_contexts_by_tag("sql", project_id="nonexistent_project")
        
        assert len(results) == 0

    @pytest.mark.asyncio
    async def test_find_contexts_by_tag_performance_common_tag(self, tags_manager_with_data):
        """Test project isolation for a tag that exists in multiple projects."""
        manager, context_ids = tags_manager_with_data
        
        # "performance" tag exists in both projects
        project_a_perf = await manager.context_service.tags_repo.find_contexts_by_tag("performance", project_id="project_a")
        project_b_perf = await manager.context_service.tags_repo.find_contexts_by_tag("performance", project_id="project_b")
        
        # Project A should have 1 performance context
        assert len(project_a_perf) == 1
        assert context_ids['project_a_sql'] in project_a_perf
        
        # Project B should have 2 performance contexts
        assert len(project_b_perf) == 2
        assert context_ids['project_b_sql'] in project_b_perf
        assert context_ids['project_b_perf'] in project_b_perf


class TestMemoryFacadeOptimization:
    """Test the optimized load_contexts logic in MemoryFacade."""

    @pytest.fixture
    async def facade_test_manager(self):
        """Create memory manager for testing MemoryFacade optimization logic."""
        db_fd, db_path = tempfile.mkstemp(suffix='.db')
        os.close(db_fd)
        
        try:
            manager = MemoryManager(db_path=db_path)
            await manager.initialize_database()
            
            # Get repositories from manager
            context_repo = manager.context_service.context_repo
            tags_repo = manager.context_service.tags_repo
            
            # Create contexts for testing the optimized tags_filter logic
            context_ids = {}
            
            context_ids['test_proj_backend'] = await context_repo.save_context(
                content="Backend implementation for test project",
                importance_level=8,
                project_id="test_project",
            )
            
            context_ids['test_proj_frontend'] = await context_repo.save_context(
                content="Frontend implementation for test project",
                importance_level=7,
                project_id="test_project",
            )
            
            context_ids['other_proj_backend'] = await context_repo.save_context(
                content="Backend implementation for other project",
                importance_level=9,
                project_id="other_project",
            )
            
            # Add tags for each context
            await tags_repo.save_context_tags(context_ids['test_proj_backend'], ["backend", "implementation"])
            await tags_repo.save_context_tags(context_ids['test_proj_frontend'], ["frontend", "implementation"])
            await tags_repo.save_context_tags(context_ids['other_proj_backend'], ["backend"])
            
            yield manager, context_ids
            
        finally:
            if os.path.exists(db_path):
                os.unlink(db_path)

    @pytest.mark.asyncio
    async def test_load_contexts_tags_filter_project_isolation_optimization(self, facade_test_manager, context_repo):
        """Test that optimized tags_filter respects project isolation using SQL-level filtering."""
        manager, context_ids = facade_test_manager
        
        # This test verifies the bug fix: tags_filter should respect project_id
        
        # Search for "backend" tag in test_project only
        test_project_backend = await manager.load_contexts(
            project_id="test_project",
            tags_filter=["backend"]
        )
        
        # Should find only the test_project backend context
        assert len(test_project_backend) == 1
        assert test_project_backend[0]['id'] == context_ids['test_proj_backend']
        assert test_project_backend[0]['project_id'] == "test_project"
        
        # Search for "backend" tag in other_project only
        other_project_backend = await manager.load_contexts(
            project_id="other_project",
            tags_filter=["backend"]
        )
        
        # Should find only the other_project backend context
        assert len(other_project_backend) == 1 
        assert other_project_backend[0]['id'] == context_ids['other_proj_backend']
        assert other_project_backend[0]['project_id'] == "other_project"

    @pytest.mark.asyncio
    async def test_load_contexts_optimization_path_usage(self, facade_test_manager, context_repo):
        """Test that the optimized code path is used when tags_filter is provided."""
        manager, context_ids = facade_test_manager
        
        # Mock the context_repo.load_contexts_by_ids to verify it's called
        original_method = manager.context_service.context_repo.load_contexts_by_ids
        call_count = 0
        
        async def mock_load_contexts_by_ids(context_ids_list):
            nonlocal call_count
            call_count += 1
            return await original_method(context_ids_list)
        
        manager.context_service.context_repo.load_contexts_by_ids = mock_load_contexts_by_ids
        
        # Use tags_filter to trigger optimized path
        results = await manager.load_contexts(
            project_id="test_project",
            tags_filter=["implementation"]
        )
        
        # Verify the optimized method was called
        assert call_count == 1
        assert len(results) == 2  # Both test_project contexts have "implementation" tag
        
        # Reset mock
        manager.context_service.context_repo.load_contexts_by_ids = original_method
